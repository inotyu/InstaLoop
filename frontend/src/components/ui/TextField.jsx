import './textfield.css'

export default function TextField({ label, hint, error, className, multiline, ...props }) {
  const id = props.id || props.name
  const Component = multiline ? 'textarea' : 'input'
  
  return (
    <div className={['field', className].filter(Boolean).join(' ')}>
      {label ? (
        <label className="field-label" htmlFor={id}>
          {label}
        </label>
      ) : null}
      <Component 
        className={multiline ? 'field-input field-area' : 'field-input'} 
        id={id} 
        {...props} 
      />
      {hint ? <div className="field-hint">{hint}</div> : null}
      {error ? <div className="field-error">{error}</div> : null}
    </div>
  )
}
