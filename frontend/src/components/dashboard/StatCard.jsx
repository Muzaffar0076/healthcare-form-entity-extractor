import React from "react";
import { Loader2 } from "lucide-react";

/**
 * StatCard: Modern SaaS metric card displaying aggregate extraction statistics.
 */
export default function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  colorTheme = "blue",
  loading = false,
}) {
  return (
    <div className={`saas-stat-card theme-${colorTheme}`}>
      <div className="stat-card-header">
        <span className="stat-card-title">{title}</span>
        {Icon && (
          <div className="stat-card-icon-wrap">
            <Icon size={18} />
          </div>
        )}
      </div>

      <div className="stat-card-body">
        {loading ? (
          <div className="stat-card-loading">
            <Loader2 size={20} className="spin-icon text-muted" />
          </div>
        ) : (
          <div className="stat-card-value">{value}</div>
        )}
        {subtitle && <p className="stat-card-subtitle">{subtitle}</p>}
      </div>
    </div>
  );
}

