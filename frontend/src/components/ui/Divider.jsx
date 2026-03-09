import './divider.css'

export default function Divider({ label = 'OU' }) {
  return (
    <div className="div">
      <div className="div-line" />
      <div className="div-label">{label}</div>
      <div className="div-line" />
    </div>
  )
}
