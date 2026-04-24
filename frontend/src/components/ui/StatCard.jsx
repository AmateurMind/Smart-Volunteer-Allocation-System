import { TrendingUp, TrendingDown, Minus } from "lucide-react";

// ─────────────────────────────────────────────────────────────────────────────
//  SVAS – Shared UI Components
//  StatCard · Card · LoadingSpinner · SkeletonLoader
// ─────────────────────────────────────────────────────────────────────────────

// ─────────────────────────────────────────────────────────────────────────────
// StatCard
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Headline KPI card shown in dashboard stat rows.
 *
 * @example
 * <StatCard
 *   label="Open Needs"
 *   value={42}
 *   icon={<AlertCircle size={22} />}
 *   iconColor="#d9534f"
 *   iconBg="#fdf2f2"
 *   trend={{ value: 12, direction: "up", label: "vs last week" }}
 * />
 */
export function StatCard({
    label,
    value,
    icon,
    iconColor = "var(--color-primary)",
    iconBg    = "var(--color-primary-50)",
    trend,          // { value: number, direction: "up"|"down"|"flat", label?: string }
    loading = false,
    onClick,
    style = {},
}) {
    if (loading) {
        return (
            <div className="stat-card" style={style}>
                <SkeletonLoader height={20} width="60%" />
                <SkeletonLoader height={36} width="40%" style={{ marginTop: 8 }} />
                <SkeletonLoader height={14} width="50%" style={{ marginTop: 8 }} />
            </div>
        );
    }

    const trendColor =
        trend?.direction === "up"
            ? "var(--color-success)"
            : trend?.direction === "down"
            ? "var(--color-danger)"
            : "var(--color-gray-400)";

    const TrendIcon =
        trend?.direction === "up"
            ? TrendingUp
            : trend?.direction === "down"
            ? TrendingDown
            : Minus;

    return (
        <div
            className="stat-card"
            onClick={onClick}
            role={onClick ? "button" : undefined}
            tabIndex={onClick ? 0 : undefined}
            style={{
                cursor: onClick ? "pointer" : "default",
                ...style,
            }}
        >
            {/* Top row: icon + label */}
            <div
                style={{
                    display:        "flex",
                    alignItems:     "center",
                    justifyContent: "space-between",
                }}
            >
                <span
                    style={{
                        fontSize:   "0.8125rem",
                        fontWeight: 500,
                        color:      "var(--color-gray-500)",
                        letterSpacing: "0.01em",
                    }}
                >
                    {label}
                </span>

                {icon && (
                    <div
                        style={{
                            width:          38,
                            height:         38,
                            borderRadius:   "0.625rem",
                            background:     iconBg,
                            display:        "flex",
                            alignItems:     "center",
                            justifyContent: "center",
                            color:          iconColor,
                            flexShrink:     0,
                        }}
                    >
                        {icon}
                    </div>
                )}
            </div>

            {/* Value */}
            <div
                style={{
                    fontSize:      "2rem",
                    fontWeight:    700,
                    color:         "var(--color-gray-900)",
                    lineHeight:    1,
                    letterSpacing: "-0.02em",
                    marginTop:     "0.25rem",
                }}
            >
                {value ?? "—"}
            </div>

            {/* Trend */}
            {trend && (
                <div
                    style={{
                        display:    "flex",
                        alignItems: "center",
                        gap:        "0.25rem",
                        marginTop:  "0.25rem",
                    }}
                >
                    <TrendIcon size={13} style={{ color: trendColor, flexShrink: 0 }} />
                    <span
                        style={{
                            fontSize:   "0.78rem",
                            fontWeight: 600,
                            color:      trendColor,
                        }}
                    >
                        {trend.value}%
                    </span>
                    {trend.label && (
                        <span
                            style={{
                                fontSize: "0.75rem",
                                color:    "var(--color-gray-400)",
                            }}
                        >
                            {trend.label}
                        </span>
                    )}
                </div>
            )}
        </div>
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// Card
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Generic container card with optional header (title + action) and footer.
 *
 * @example
 * <Card title="Recent Needs" action={<button>View all</button>}>
 *   <p>Content goes here</p>
 * </Card>
 */
export function Card({
    children,
    title,
    subtitle,
    action,
    footer,
    noPadding = false,
    hover     = false,
    style     = {},
    className = "",
    onClick,
}) {
    return (
        <div
            className={`card ${hover ? "card-hover" : ""} ${className}`}
            onClick={onClick}
            role={onClick ? "button" : undefined}
            tabIndex={onClick ? 0 : undefined}
            style={{
                padding:        noPadding ? 0 : undefined,
                cursor:         onClick ? "pointer" : "default",
                display:        "flex",
                flexDirection:  "column",
                gap:            title || subtitle ? "1rem" : 0,
                ...style,
            }}
        >
            {/* Card header */}
            {(title || action) && (
                <div
                    style={{
                        display:        "flex",
                        alignItems:     "flex-start",
                        justifyContent: "space-between",
                        gap:            "0.75rem",
                        padding:        noPadding ? "1.5rem 1.5rem 0" : 0,
                    }}
                >
                    <div>
                        {title && (
                            <h3
                                style={{
                                    fontSize:   "1rem",
                                    fontWeight: 600,
                                    color:      "var(--color-gray-900)",
                                    margin:     0,
                                }}
                            >
                                {title}
                            </h3>
                        )}
                        {subtitle && (
                            <p
                                style={{
                                    fontSize:  "0.8125rem",
                                    color:     "var(--color-gray-500)",
                                    marginTop: "0.2rem",
                                }}
                            >
                                {subtitle}
                            </p>
                        )}
                    </div>
                    {action && (
                        <div style={{ flexShrink: 0 }}>{action}</div>
                    )}
                </div>
            )}

            {/* Card body */}
            <div style={{ padding: noPadding ? "0 1.5rem" : 0, flex: 1 }}>
                {children}
            </div>

            {/* Card footer */}
            {footer && (
                <div
                    style={{
                        borderTop:  "1px solid var(--color-brand-cream)",
                        padding:    noPadding ? "0.875rem 1.5rem" : "0.875rem 0 0",
                        marginTop:  "auto",
                    }}
                >
                    {footer}
                </div>
            )}
        </div>
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// LoadingSpinner
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Animated spinner for async loading states.
 *
 * @example
 * <LoadingSpinner size={32} color="var(--color-primary)" />
 * <LoadingSpinner label="Fetching volunteers…" />
 */
export function LoadingSpinner({
    size    = 24,
    color   = "var(--color-primary)",
    label,
    center  = false,
    style   = {},
}) {
    const spinner = (
        <div
            style={{
                display:        "inline-flex",
                flexDirection:  "column",
                alignItems:     "center",
                justifyContent: "center",
                gap:            "0.625rem",
                ...style,
            }}
        >
            {/* SVG spinner ring */}
            <svg
                width={size}
                height={size}
                viewBox="0 0 24 24"
                fill="none"
                style={{
                    animation:   "spin 0.8s linear infinite",
                    flexShrink:  0,
                }}
                aria-label="Loading"
                role="status"
            >
                <style>{`
                    @keyframes spin {
                        from { transform: rotate(0deg);   }
                        to   { transform: rotate(360deg); }
                    }
                `}</style>
                {/* Track */}
                <circle
                    cx="12" cy="12" r="9"
                    stroke={color}
                    strokeOpacity="0.2"
                    strokeWidth="2.5"
                />
                {/* Arc */}
                <path
                    d="M12 3 A9 9 0 0 1 21 12"
                    stroke={color}
                    strokeWidth="2.5"
                    strokeLinecap="round"
                />
            </svg>

            {label && (
                <span
                    style={{
                        fontSize:  "0.8125rem",
                        color:     "var(--color-gray-500)",
                        fontWeight: 450,
                    }}
                >
                    {label}
                </span>
            )}
        </div>
    );

    if (center) {
        return (
            <div
                style={{
                    display:        "flex",
                    alignItems:     "center",
                    justifyContent: "center",
                    width:          "100%",
                    padding:        "3rem 1rem",
                }}
            >
                {spinner}
            </div>
        );
    }

    return spinner;
}

// ─────────────────────────────────────────────────────────────────────────────
// SkeletonLoader
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Shimmer skeleton placeholder for content that is still loading.
 *
 * @example
 * <SkeletonLoader height={20} width="60%" />
 * <SkeletonLoader variant="circle" width={40} height={40} />
 * <SkeletonLoader variant="card" />
 * <SkeletonLoader count={3} height={14} gap={8} />
 */
export function SkeletonLoader({
    width    = "100%",
    height   = 16,
    variant  = "rect",   // "rect" | "circle" | "card" | "text"
    count    = 1,        // repeat N skeleton lines
    gap      = 6,        // gap between repeated lines (px)
    rounded  = false,    // full border-radius
    style    = {},
    className = "",
}) {
    const sharedStyle = {
        display: "block",
        width,
        height,
        borderRadius:
            variant === "circle"
                ? "50%"
                : rounded || variant === "text"
                ? "999px"
                : "0.375rem",
        ...style,
    };

    // Card skeleton preset
    if (variant === "card") {
        return (
            <div
                className={`card ${className}`}
                style={{ display: "flex", flexDirection: "column", gap: 12 }}
            >
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <span
                        className="skeleton"
                        style={{ width: 40, height: 40, borderRadius: "0.625rem", flexShrink: 0 }}
                    />
                    <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 6 }}>
                        <span className="skeleton" style={{ height: 14, width: "60%" }} />
                        <span className="skeleton" style={{ height: 12, width: "40%" }} />
                    </div>
                </div>
                <span className="skeleton" style={{ height: 12, width: "100%" }} />
                <span className="skeleton" style={{ height: 12, width: "80%" }} />
                <span className="skeleton" style={{ height: 12, width: "90%" }} />
            </div>
        );
    }

    if (count > 1) {
        return (
            <div
                style={{
                    display:       "flex",
                    flexDirection: "column",
                    gap:           gap,
                }}
                className={className}
            >
                {Array.from({ length: count }).map((_, i) => (
                    <span
                        key={i}
                        className="skeleton"
                        style={{
                            ...sharedStyle,
                            /* Stagger widths for text-line look */
                            width:
                                variant === "text"
                                    ? i === count - 1
                                        ? "65%"   // last line shorter
                                        : "100%"
                                    : width,
                        }}
                    />
                ))}
            </div>
        );
    }

    return (
        <span
            className={`skeleton ${className}`}
            style={sharedStyle}
        />
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// PageLoader  –  full-page centred spinner (used in route lazy loading)
// ─────────────────────────────────────────────────────────────────────────────

export function PageLoader({ label = "Loading…" }) {
    return (
        <div
            style={{
                display:        "flex",
                alignItems:     "center",
                justifyContent: "center",
                minHeight:      "100svh",
                background:     "var(--color-surface)",
                flexDirection:  "column",
                gap:            "1.25rem",
            }}
        >
            {/* Logo mark */}
            <div
                style={{
                    width:          48,
                    height:         48,
                    borderRadius:   "0.875rem",
                    background:
                        "linear-gradient(135deg, var(--color-primary-dark) 0%, var(--color-accent) 100%)",
                    display:        "flex",
                    alignItems:     "center",
                    justifyContent: "center",
                    boxShadow:      "0 4px 16px rgba(164,114,81,0.3)",
                }}
            >
                <svg
                    width="26" height="26" viewBox="0 0 24 24"
                    fill="none" stroke="#fff" strokeWidth="2.5"
                    strokeLinecap="round" strokeLinejoin="round"
                >
                    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
                </svg>
            </div>

            <LoadingSpinner size={28} label={label} />
        </div>
    );
}

export default StatCard;
