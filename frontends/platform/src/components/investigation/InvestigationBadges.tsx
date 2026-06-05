import {
  AlertTriangle,
  Bell,
  Calendar,
  CheckCircle2,
  CircleX,
  Clock,
  Eye,
  Hand,
  Headphones,
  Loader2,
  PauseCircle,
  Shield,
  ShieldCheck,
  TicketCheck,
  User,
} from "lucide-react";
import { Badge } from "@/components/ui";
import { cn } from "@/lib/utils";
import {
  STATUS_LABELS,
  TRIGGER_LABELS,
  type InvestigationAuthority,
  type InvestigationSeverity,
  type InvestigationStatus,
  type InvestigationTrigger,
} from "@/types/investigation";

const STATUS_TONE: Record<
  InvestigationStatus,
  "success" | "warning" | "danger" | "info" | "neutral" | "accent"
> = {
  running: "info",
  queued: "neutral",
  needs_review: "warning",
  resolved: "success",
  escalated: "danger",
  cancelled: "neutral",
};

const STATUS_ICON: Record<InvestigationStatus, React.ReactNode> = {
  running: <Loader2 size={10} className="animate-spin" />,
  queued: <Clock size={10} />,
  needs_review: <Hand size={10} />,
  resolved: <CheckCircle2 size={10} />,
  escalated: <AlertTriangle size={10} />,
  cancelled: <CircleX size={10} />,
};

export function StatusBadge({
  status,
  size = "sm",
}: {
  status: InvestigationStatus;
  size?: "xs" | "sm" | "md";
}) {
  return (
    <Badge tone={STATUS_TONE[status]} size={size} icon={STATUS_ICON[status]}>
      {STATUS_LABELS[status]}
    </Badge>
  );
}

const SEV_TONE: Record<
  InvestigationSeverity,
  "danger" | "warning" | "info" | "neutral"
> = {
  P1: "danger",
  P2: "warning",
  P3: "info",
  P4: "neutral",
};

export function SeverityBadge({
  severity,
  size = "sm",
}: {
  severity: InvestigationSeverity;
  size?: "xs" | "sm" | "md";
}) {
  return (
    <Badge tone={SEV_TONE[severity]} size={size} mono dot>
      {severity}
    </Badge>
  );
}

const TRIGGER_ICON: Record<InvestigationTrigger, React.ReactNode> = {
  manual: <User size={10} />,
  alert: <Bell size={10} />,
  ticket: <TicketCheck size={10} />,
  customer: <Headphones size={10} />,
  scheduled: <Calendar size={10} />,
  compliance: <Shield size={10} />,
};

export function TriggerBadge({
  trigger,
  triggerRef,
  size = "sm",
}: {
  trigger: InvestigationTrigger;
  triggerRef?: string;
  size?: "xs" | "sm" | "md";
}) {
  return (
    <Badge tone="outline" size={size} icon={TRIGGER_ICON[trigger]}>
      <span className="font-medium">{TRIGGER_LABELS[trigger]}</span>
      {triggerRef && (
        <span className="font-mono text-text-faint">{triggerRef}</span>
      )}
    </Badge>
  );
}

const AUTHORITY_TONE: Record<
  InvestigationAuthority,
  "accent" | "warning" | "danger"
> = {
  read_only: "accent",
  approve_writes: "warning",
  autonomous: "danger",
};

const AUTHORITY_ICON: Record<InvestigationAuthority, React.ReactNode> = {
  read_only: <Eye size={10} />,
  approve_writes: <ShieldCheck size={10} />,
  autonomous: <PauseCircle size={10} />,
};

export function AuthorityBadge({
  authority,
  size = "sm",
}: {
  authority: InvestigationAuthority;
  size?: "xs" | "sm" | "md";
}) {
  const labels: Record<InvestigationAuthority, string> = {
    read_only: "Read-only",
    approve_writes: "Writes need OK",
    autonomous: "Autonomous",
  };
  return (
    <Badge
      tone={AUTHORITY_TONE[authority]}
      size={size}
      icon={AUTHORITY_ICON[authority]}
      className={cn("uppercase tracking-wide")}
    >
      {labels[authority]}
    </Badge>
  );
}
