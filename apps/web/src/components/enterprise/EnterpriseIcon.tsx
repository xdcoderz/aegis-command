export type EnterpriseIconName =
  | "activity"
  | "alert"
  | "arrow"
  | "check"
  | "clock"
  | "key"
  | "refresh"
  | "search"
  | "shield"
  | "user";

interface EnterpriseIconProps {
  name: EnterpriseIconName;
  size?: number;
}

export function EnterpriseIcon({ name, size = 18 }: EnterpriseIconProps) {
  const common = {
    fill: "none",
    stroke: "currentColor",
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    strokeWidth: 1.7,
  };

  const paths: Record<EnterpriseIconName, React.ReactNode> = {
    activity: <path d="M3 12h4l2.1-6 3.6 12 2.2-6H21" />,
    alert: (
      <>
        <path d="M10.3 4.2 2.7 17.4A1.8 1.8 0 0 0 4.3 20h15.4a1.8 1.8 0 0 0 1.6-2.6L13.7 4.2a2 2 0 0 0-3.4 0Z" />
        <path d="M12 9v4M12 16.5h.01" />
      </>
    ),
    arrow: <path d="M5 12h14m-5-5 5 5-5 5" />,
    check: <path d="m5 12 4 4L19 6" />,
    clock: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" />
      </>
    ),
    key: (
      <>
        <circle cx="8" cy="15" r="4" />
        <path d="m11 12 8-8m-3 3 2 2m-5 1 2 2" />
      </>
    ),
    refresh: (
      <>
        <path d="M20 7v5h-5" />
        <path d="M18.5 15a7.5 7.5 0 1 1-.9-7.8L20 9" />
      </>
    ),
    search: (
      <>
        <circle cx="11" cy="11" r="6.5" />
        <path d="m16 16 4 4" />
      </>
    ),
    shield: (
      <>
        <path d="M12 3 5 6v5c0 4.8 2.8 8.1 7 10 4.2-1.9 7-5.2 7-10V6l-7-3Z" />
        <path d="m9 12 2 2 4-5" />
      </>
    ),
    user: (
      <>
        <circle cx="12" cy="8" r="3.5" />
        <path d="M5 21c.7-4.1 3-6 7-6s6.3 1.9 7 6" />
      </>
    ),
  };

  return (
    <svg
      aria-hidden="true"
      className="enterprise-icon"
      height={size}
      viewBox="0 0 24 24"
      width={size}
      {...common}
    >
      {paths[name]}
    </svg>
  );
}
