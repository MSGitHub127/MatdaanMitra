import { FileText, MapPin, Phone, AlertCircle } from 'lucide-react';

export default function QuickNav() {
  const navItems = [
    { icon: FileText, label: 'Forms', href: '#forms' },
    { icon: MapPin, label: 'Find ERO', href: '#ero' },
    { icon: Phone, label: 'Helpline', href: '#helpline' },
    { icon: AlertCircle, label: 'Grievance', href: '#grievance' },
  ];

  return (
    <div>
      <h3 className="text-xs text-ink-faint uppercase tracking-wider mb-3">Quick Actions</h3>
      <div className="space-y-1">
        {navItems.map((item) => (
          <a
            key={item.href}
            href={item.href}
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-ink-dim hover:bg-card hover:text-ink transition-colors"
          >
            <item.icon className="w-4 h-4" />
            <span>{item.label}</span>
          </a>
        ))}
      </div>
    </div>
  );
}
