from esphome import automation, pins
import esphome.codegen as cg
from esphome.components import libretiny, output
import esphome.config_validation as cv
from esphome.const import CONF_FREQUENCY, CONF_ID, CONF_PIN
from esphome.types import ConfigType

DEPENDENCIES = ["libretiny"]

libretinypwm_ns = cg.esphome_ns.namespace("libretiny_pwm")
LibreTinyPWM = libretinypwm_ns.class_("LibreTinyPWM", output.FloatOutput, cg.Component)

validate_frequency = cv.All(cv.frequency, cv.float_range(min=0, min_included=False))


def _validate_pwm(config: ConfigType) -> ConfigType:
    if not libretiny.has_pwm():
        raise cv.Invalid(
            f"PWM on {libretiny.get_libretiny_family()} needs LibreTiny "
            f"{libretiny.LN882H_PWM_VERSION} or later"
        )
    return config


CONFIG_SCHEMA = cv.All(
    _validate_pwm,
    output.FLOAT_OUTPUT_SCHEMA.extend(
        {
            cv.Required(CONF_ID): cv.declare_id(LibreTinyPWM),
            cv.Required(CONF_PIN): pins.internal_gpio_output_pin_schema,
            cv.Optional(CONF_FREQUENCY, default="1kHz"): validate_frequency,
        }
    ).extend(cv.COMPONENT_SCHEMA),
)


async def to_code(config: ConfigType) -> None:
    gpio = await cg.gpio_pin_expression(config[CONF_PIN])
    var = cg.new_Pvariable(config[CONF_ID], gpio)
    await cg.register_component(var, config)
    await output.register_output(var, config)
    cg.add(var.set_frequency(config[CONF_FREQUENCY]))


automation.register_apply_action(
    "output.libretiny_pwm.set_frequency",
    cv.Schema(
        {
            cv.Required(CONF_ID): cv.use_id(LibreTinyPWM),
            cv.Required(CONF_FREQUENCY): cv.templatable(validate_frequency),
        }
    ),
    automation.ApplyField(CONF_FREQUENCY, "update_frequency", cg.float_),
)
