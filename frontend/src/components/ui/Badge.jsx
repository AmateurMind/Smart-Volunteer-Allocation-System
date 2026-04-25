
// ─────────────────────────────────────────────────────────────────────────────
//  SVAS – Badge Component
//  Reusable pill/chip badge with all SVAS colour variants.
// ─────────────────────────────────────────────────────────────────────────────

// ── Variant → CSS-class map ───────────────────────────────────────────────────
const VARIANT_CLASS = {
    success:   "badge badge-success",
    warning:   "badge badge-warning",
    danger:    "badge badge-danger",
    info:      "badge badge-info",
    primary:   "badge badge-primary",
    accent:    "badge badge-accent",
    neutral:   "badge badge-neutral",
    high:      "badge badge-high",
    medium:    "badge badge-medium",
    low:       "badge badge-low",
    food:      "badge badge-food",
    health:    "badge badge-health",
    education: "badge badge-education",
    shelter:   "badge badge-shelter",
    clothing:  "badge badge-clothing",
    other:     "badge badge-other",
};

// ── Urgency → variant helper ──────────────────────────────────────────────────
export function urgencyVariant(urgency = "") {
    switch (urgency.toUpperCase()) {
        case "HIGH":   return "high";
        case "MEDIUM": return "medium";
        case "LOW":    return "low";
        default:       return "neutral";
    }
}

// ── Category → variant helper ─────────────────────────────────────────────────
export function categoryVariant(category = "") {
    switch (category.toUpperCase()) {
        case "FOOD":      return "food";
        case "HEALTH":    return "health";
        case "EDUCATION": return "education";
        case "SHELTER":   return "shelter";
        case "CLOTHING":  return "clothing";
        default:          return "other";
    }
}

// ── Status → variant helper ───────────────────────────────────────────────────
export function statusVariant(status = "") {
    switch (status.toUpperCase()) {
        case "OPEN":
        case "AVAILABLE":
        case "COMPLETED":
        case "VERIFIED":
        case "RESOLVED":
            return "success";

        case "ASSIGNED":
        case "ACCEPTED":
        case "IN_PROGRESS":
        case "ON_ASSIGNMENT":
            return "warning";

        case "PENDING":
            return "info";

        case "CANCELLED":
        case "REJECTED":
        case "INACTIVE":
        case "CLOSED":
            return "danger";

        default:
            return "neutral";
    }
}

// ── Size styles ───────────────────────────────────────────────────────────────
const SIZE_STYLES = {
    xs: { fontSize: "0.65rem",  padding: "0.125rem 0.45rem" },
    sm: { fontSize: "0.72rem",  padding: "0.15rem  0.55rem" },
    md: { fontSize: "0.75rem",  padding: "0.2rem   0.65rem" },   // default
    lg: { fontSize: "0.8125rem",padding: "0.25rem  0.8rem"  },
};

// ─────────────────────────────────────────────────────────────────────────────
// Badge
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Reusable status / label badge.
 *
 * @example
 * <Badge variant="high">HIGH</Badge>
 * <Badge variant={urgencyVariant("MEDIUM")}>MEDIUM</Badge>
 * <Badge variant={categoryVariant("FOOD")} dot>Food</Badge>
 * <Badge variant="success" size="lg">Completed</Badge>
 */
export default function Badge({
    children,
    variant = "neutral",
    size    = "md",
    dot     = false,
    icon    = null,
    style   = {},
    className = "",
    title,
    onClick,
}) {
    const baseClass = VARIANT_CLASS[variant] ?? VARIANT_CLASS.neutral;
    const sizeStyle = SIZE_STYLES[size]      ?? SIZE_STYLES.md;

    return (
        <span
            className={`${baseClass} ${className}`}
            title={title}
            onClick={onClick}
            role={onClick ? "button" : undefined}
            tabIndex={onClick ? 0 : undefined}
            style={{
                ...sizeStyle,
                cursor: onClick ? "pointer" : "default",
                userSelect: "none",
                ...style,
            }}
        >
            {/* Leading dot indicator */}
            {dot && (
                <span
                    style={{
                        width: "6px",
                        height: "6px",
                        borderRadius: "50%",
                        background: "currentColor",
                        display: "inline-block",
                        flexShrink: 0,
                    }}
                />
            )}

            {/* Optional leading icon */}
            {icon && (
                <span
                    style={{
                        display: "inline-flex",
                        alignItems: "center",
                        flexShrink: 0,
                        lineHeight: 1,
                    }}
                >
                    {icon}
                </span>
            )}

            {children}
        </span>
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// Convenience wrappers
// ─────────────────────────────────────────────────────────────────────────────

/** Badge pre-configured for urgency levels. */
export function UrgencyBadge({ urgency, size, style, className }) {
    const labels = { HIGH: "High", MEDIUM: "Medium", LOW: "Low" };
    const label  = labels[urgency?.toUpperCase()] ?? urgency ?? "Unknown";
    return (
        <Badge
            variant={urgencyVariant(urgency)}
            size={size}
            dot
            style={style}
            className={className}
        >
            {label}
        </Badge>
    );
}

/** Badge pre-configured for need categories. */
export function CategoryBadge({ category, size, style, className }) {
    const labels = {
        FOOD: "Food", HEALTH: "Health", EDUCATION: "Education",
        SHELTER: "Shelter", CLOTHING: "Clothing", OTHER: "Other",
    };
    const label = labels[category?.toUpperCase()] ?? category ?? "Other";
    return (
        <Badge
            variant={categoryVariant(category)}
            size={size}
            style={style}
            className={className}
        >
            {label}
        </Badge>
    );
}

/** Badge pre-configured for task / need lifecycle statuses. */
export function StatusBadge({ status, size, style, className }) {
    const label = status
        ? status.charAt(0).toUpperCase() + status.slice(1).toLowerCase().replace(/_/g, " ")
        : "Unknown";
    return (
        <Badge
            variant={statusVariant(status)}
            size={size}
            dot
            style={style}
            className={className}
        >
            {label}
        </Badge>
    );
}

/** Badge for volunteer skill tags. */
export function SkillBadge({ skill, size = "sm", style, className }) {
    const labels = {
        MEDICAL:    "Medical",
        EDUCATION:  "Education",
        LOGISTICS:  "Logistics",
        COUNSELING: "Counseling",
        DRIVING:    "Driving",
        COOKING:    "Cooking",
        GENERAL:    "General",
    };
    const label = labels[skill?.toUpperCase()] ?? skill ?? skill;
    return (
        <Badge
            variant="primary"
            size={size}
            style={style}
            className={className}
        >
            {label}
        </Badge>
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// Badge
// ─────────────────────────────────────────────────────────────────────────────
