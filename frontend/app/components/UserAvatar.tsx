"use client";

interface UserAvatarProps {
  username: string;
  role: string;
  avatarUrl?: string | null;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const ROLE_BG: Record<string, string> = {
  super_admin: "bg-red-500",
  admin:       "bg-orange-500",
  editor:      "bg-blue-500",
  viewer:      "bg-gray-500",
};

const SIZE_CLS = {
  sm: "h-8 w-8 text-sm",
  md: "h-9 w-9 text-sm",
  lg: "h-14 w-14 text-xl",
};

export default function UserAvatar({ username, role, avatarUrl, size = "md", className = "" }: UserAvatarProps) {
  const initials = username?.[0]?.toUpperCase() ?? "?";
  const bg = ROLE_BG[role] ?? ROLE_BG.viewer;
  const sizeCls = SIZE_CLS[size];

  if (avatarUrl) {
    return (
      <img
        src={avatarUrl}
        alt={username}
        className={`${sizeCls} rounded-full object-cover ${className}`}
      />
    );
  }

  return (
    <span
      className={`inline-flex items-center justify-center rounded-full font-bold text-white ${bg} ${sizeCls} ${className}`}
    >
      {initials}
    </span>
  );
}
