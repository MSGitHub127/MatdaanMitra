# Security Implementation

## Threat Model

| Threat | Mitigation |
|--------|------------|
| Prompt injection | Blocklist patterns validated in Pydantic validator |
| PII exposure | EPIC numbers Fernet-encrypted before Firestore write |
| Session hijacking | Firebase ID token verified server-side on every request |
| Rate abuse | Redis sliding window: 30 req/min per UID |
| Political manipulation | Regex guardrail node in every agent response |
| Hallucinated law | Confidence threshold 0.75 → escalation to 1950 helpline |
| Data residency | All GCP resources in `asia-south1` (Mumbai) |

## EPIC Number Encryption

EPIC numbers are Personally Identifiable Information (PII) and must never be stored in plaintext.

```python
from cryptography.fernet import Fernet

def encrypt_epic(epic_number: str) -> str:
    """EPIC numbers are PII — never stored in plaintext"""
    key = get_secret("fernet-encryption-key")
    f = Fernet(key.encode())
    return f.encrypt(epic_number.encode()).decode()
```

## Content Security Policy

```javascript
// next.config.js
const securityHeaders = [
  {
    key: 'Content-Security-Policy',
    value: [
      "default-src 'self'",
      "script-src 'self' 'unsafe-eval' https://apis.google.com",
      "connect-src 'self' https://*.firebaseio.com https://*.googleapis.com",
      "frame-ancestors 'none'",
    ].join('; ')
  },
  { key: 'X-Frame-Options',        value: 'DENY'      },
  { key: 'X-Content-Type-Options', value: 'nosniff'   },
  { key: 'Referrer-Policy',        value: 'strict-origin-when-cross-origin' },
]
```

## Input Validation

All user inputs are sanitized and validated:

```python
class ChatRequest(BaseModel):
    session_id: constr(pattern=r'^[a-zA-Z0-9_-]{10,50}$')
    message: constr(min_length=1, max_length=2000)
    language: str = "en"

    @validator('message')
    def sanitize_message(cls, v):
        cleaned = bleach.clean(v, tags=[], strip=True)
        INJECTION_PATTERNS = [
            "ignore previous instructions", "you are now",
            "act as if", "disregard your", "system prompt", "jailbreak",
        ]
        for pattern in INJECTION_PATTERNS:
            if pattern.lower() in cleaned.lower():
                raise ValueError("Invalid input detected")
        return cleaned
```

## Rate Limiting

Sliding window rate limiter using Redis:

```python
class RateLimiter:
    """
    Sliding window rate limiter using Redis.
    30 requests/minute per Firebase UID.
    """
    async def check(self, uid: str, endpoint: str):
        key = f"rate:{uid}:{endpoint}"
        pipe = self.redis.pipeline()
        now = time.time()
        window_start = now - 60

        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, 60)

        _, _, count, _ = await pipe.execute()

        if count > 30:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please wait before asking again.",
                headers={"Retry-After": "60"}
            )
```

## Firestore Security Rules

```javascript
// firestore.rules
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /sessions/{sessionId} {
      allow read, write: if request.auth != null
        && request.auth.uid == resource.data.uid;

      match /messages/{msgId} {
        allow read: if request.auth != null
          && get(/databases/$(database)/documents/sessions/$(sessionId))
             .data.uid == request.auth.uid;
        allow create: if request.auth != null
          && request.resource.data.keys()
             .hasAll(['role', 'content', 'timestamp'])
          && request.resource.data.content.size() < 4000;
      }
    }
  }
}
```

## Political Content Guardrail

```python
POLITICAL_PATTERNS = [
    r'\b(BJP|Congress|AAP|TMC|NCP|SP|BSP|JDU)\b',
    r'\b(Modi|Gandhi|Shah|Rahul|Mamata)\b',
    r'\b(vote for|support|endorse|oppose)\b.*\b(party|candidate)\b',
    r'\b(election results?|polling|exit poll|opinion poll)\b',
]

def guardrail_node(state: AgentState) -> AgentState:
    response = state["final_response"]

    for pattern in POLITICAL_PATTERNS:
        if re.search(pattern, response, re.IGNORECASE):
            return {
                **state,
                "final_response": (
                    "I'm designed to assist only with voter registration "
                    "procedures — not electoral politics. Is there anything "
                    "about your registration I can help with?"
                ),
                "requires_escalation": False,
            }
    return {**state, "final_response": response}
```

## Confidence Threshold

Low-confidence responses trigger escalation to official helpline:

```python
if state["confidence_score"] < 0.75:
    return {
        **state,
        "final_response": (
            "I don't have verified official data for this query. "
            "Please check eci.gov.in or call the National Voter "
            "Helpline at 1950 for authoritative information."
        ),
        "requires_escalation": True,
    }
```
