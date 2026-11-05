import React from 'react';

export interface LogoProps {
  /**
   * Color theme:
   * - 'dark' (default): dark navy #0F172A on light backgrounds
   * - 'white': white #FFFFFF on the blue panel
   */
  variant?: 'dark' | 'white';
  /**
   * Font size presets
   */
  size?: 'sm' | 'md' | 'lg' | 'xl' | '2xl';
  /**
   * Optional custom CSS classes
   */
  className?: string;
}

const sizeClasses: Record<NonNullable<LogoProps['size']>, string> = {
  sm: 'text-lg',
  md: 'text-2xl',
  lg: 'text-3xl',
  xl: 'text-4xl',
  '2xl': 'text-5xl',
};

/**
 * Standard ShelfWise logo component.
 * Rendered using "Times New Roman", Times, serif; font-weight: 400; no italics, no icon.
 */
export const Logo: React.FC<LogoProps> = ({
  variant = 'dark',
  size = 'md',
  className = '',
}) => {
  const color = variant === 'white' ? '#FFFFFF' : '#0F172A';

  return (
    <span
      className={`inline-block select-none leading-none tracking-tight ${sizeClasses[size]} ${className}`}
      style={{
        fontFamily: '"Times New Roman", Times, serif',
        fontWeight: 400,
        fontStyle: 'normal',
        color,
      }}
    >
      ShelfWise
    </span>
  );
};

export default Logo;

