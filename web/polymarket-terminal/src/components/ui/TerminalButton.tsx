import type { ButtonHTMLAttributes, ReactNode } from "react";

type TerminalButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  tone?: "default" | "accent" | "danger";
  icon?: ReactNode;
};

export function TerminalButton({
  children,
  className,
  icon,
  tone = "default",
  type = "button",
  ...props
}: TerminalButtonProps) {
  const classes = ["terminal-button", `terminal-button-${tone}`, className]
    .filter(Boolean)
    .join(" ");

  return (
    <button className={classes} type={type} {...props}>
      {icon ? <span className="terminal-button-icon">{icon}</span> : null}
      <span>{children}</span>
    </button>
  );
}
