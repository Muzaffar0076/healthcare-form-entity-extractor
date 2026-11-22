import React, { useEffect, useRef } from "react";

/**
 * Reusable component for rendering clinical text with synchronized, interactive entity highlights.
 *
 * Supports:
 * - Sorted non-overlapping entity offset slicing.
 * - Bi-directional interaction: clicking a highlighted entity triggers onSelectEntity.
 * - Auto-scroll when selectedEntityIndex changes.
 * - Full keyboard accessibility (tabIndex, Enter/Space triggering, aria-label).
 */
export default function HighlightedText({
  text,
  entities = [],
  selectedEntityIndex = null,
  onSelectEntity = null,
  className = "highlight-display",
  style = {},
  idPrefix = "ent-highlight-",
}) {
  const selectedRef = useRef(null);

  // Auto-scroll selected mark into view smoothly when selectedEntityIndex changes
  useEffect(() => {
    if (selectedEntityIndex !== null && selectedRef.current) {
      selectedRef.current.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
        inline: "nearest",
      });
    }
  }, [selectedEntityIndex]);

  if (!text) return null;

  if (!entities || entities.length === 0) {
    return (
      <div className={className} style={style}>
        <span>{text}</span>
      </div>
    );
  }

  // Sort entities by start offset to reconstruct text segments in order
  const sorted = [...entities].sort((a, b) => a.start - b.start);
  const elements = [];
  let lastIndex = 0;

  sorted.forEach((ent, idx) => {
    // Append leading plain text before this entity
    if (ent.start > lastIndex) {
      elements.push(
        <span key={`text-seg-${lastIndex}`}>{text.slice(lastIndex, ent.start)}</span>
      );
    }

    const isSelected = selectedEntityIndex === idx;
    const isInteractive = typeof onSelectEntity === "function";

    elements.push(
      <mark
        key={`${idPrefix}${idx}-${ent.start}`}
        ref={isSelected ? selectedRef : null}
        id={`${idPrefix}${idx}`}
        className={`entity-span entity-${ent.label} ${isSelected ? "selected" : ""} ${
          isInteractive ? "interactive" : ""
        }`}
        tabIndex={isInteractive ? 0 : undefined}
        role={isInteractive ? "button" : undefined}
        aria-label={`${ent.label}: ${text.slice(ent.start, ent.end)}`}
        aria-pressed={isInteractive ? isSelected : undefined}
        onClick={() => {
          if (isInteractive) {
            onSelectEntity(idx, ent);
          }
        }}
        onKeyDown={(e) => {
          if (isInteractive && (e.key === "Enter" || e.key === " ")) {
            e.preventDefault();
            onSelectEntity(idx, ent);
          }
        }}
      >
        {text.slice(ent.start, ent.end)}
        <span className={`entity-tag tag-${ent.label}`}>{ent.label}</span>
      </mark>
    );

    lastIndex = ent.end;
  });

  // Append any trailing plain text
  if (lastIndex < text.length) {
    elements.push(<span key="text-seg-tail">{text.slice(lastIndex)}</span>);
  }

  return (
    <div className={className} style={style} role="region" aria-label="Highlighted Document Text">
      {elements}
    </div>
  );
}

