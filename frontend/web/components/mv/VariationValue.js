import React from 'react'
import ValueEditor from 'components/ValueEditor' // we need this to make JSX compile
import Constants from 'common/constants'

const VariationValue = ({
  disabled,
  index,
  onChange,
  onRemove,
  readOnlyValue,
  value,
  weightTitle,
}) => (
  <div className='panel panel--flat panel-without-heading mb-2'>
    <div className='panel-content'>
      <Row>
        <div className='flex flex-1'>
          <InputGroup
            component={
              <ValueEditor
                data-test={`featureVariationValue${index}`}
                name='featureValue'
                className='full-width'
                value={Utils.getTypedValue(Utils.featureStateToValue(value))}
                disabled={disabled || readOnlyValue}
                onChange={(e) => {
                  onChange({
                    ...value,
                    ...Utils.valueToFeatureState(Utils.safeParseEventValue(e)),
                  })
                }}
                placeholder="e.g. 'big' "
              />
            }
            tooltip={Constants.strings.REMOTE_CONFIG_DESCRIPTION_VARIATION}
            title='Variation Value'
          />
        </div>
        <div className='ml-2' style={{ width: 210 }}>
          <InputGroup
            type='text'
            data-test={`featureVariationWeight${Utils.featureStateToValue(
              value,
            )}`}
            onChange={(e) => {
              onChange({
                ...value,
                default_percentage_allocation: Utils.safeParseEventValue(e)
                  ? parseInt(Utils.safeParseEventValue(e))
                  : null,
              })
            }}
            value={value.default_percentage_allocation}
            inputProps={{
              maxLength: 3,
              readOnly: disabled,
              style: { marginTop: 2 },
            }}
            title={weightTitle}
          />
        </div>
        {!!onRemove && (
          <div className='ml-2' style={{ marginTop: 22, width: 30 }}>
            <button
              onClick={onRemove}
              id='delete-multivariate'
              type='button'
              className='btn btn--with-icon ml-auto btn--remove'
            >
              <RemoveIcon />
            </button>
          </div>
        )}
      </Row>
    </div>
  </div>
)

export default VariationValue
