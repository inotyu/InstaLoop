import clsx from 'clsx'
import './button.css'

export default function Button({
  as: As = 'button',
  variant = 'primary',
  size = 'md',
  className,
  disabled,
  loading,
  children,
  ...props
}) {
  return (
    <As
      className={clsx('btn', `btn-${variant}`, `btn-${size}`, className, { 'loading': loading })}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? 'Carregando...' : children}
    </As>
  )
}
