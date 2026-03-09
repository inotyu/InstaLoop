import './publicshell.css'

export default function PublicShell({ children }) {
  return (
    <div className="pub">
      <div className="pub-inner">{children}</div>
    </div>
  )
}
