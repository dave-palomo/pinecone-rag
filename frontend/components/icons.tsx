type IconProps = {
  className?: string;
};

export function PlusIcon({ className }: IconProps) {
  return (
    <svg
      className={className}
      aria-hidden="true"
      viewBox="0 0 20 20"
      fill="none"
    >
      <path d="M10 3.5v13M3.5 10h13" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}
