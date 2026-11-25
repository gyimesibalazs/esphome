from esphome import pins
import esphome.codegen as cg
from esphome.components import output
from esphome.components.libretiny import get_libretiny_family
from esphome.components.libretiny.const import FAMILY_BK7231Q, FAMILY_BK7238
import esphome.config_validation as cv
from esphome.const import CONF_ID, CONF_METHOD, CONF_MIN_POWER
from esphome.core import CORE
import esphome.final_validate as fv
from esphome.types import ConfigType

CODEOWNERS = ["@glmnet"]

gpio_ns = cg.esphome_ns.namespace("gpio")

ac_dimmer_ns = cg.esphome_ns.namespace("ac_dimmer")
AcDimmer = ac_dimmer_ns.class_("AcDimmer", output.FloatOutput, cg.Component)

DimMethod = ac_dimmer_ns.enum("DimMethod")
DIM_METHODS = DimMethod.options(
    "LEADING_PULSE", "LEADING", "TRAILING", prefix="DIM_METHOD_"
)

ZC_INTERRUPT_TYPES = {
    "RISING": gpio_ns.INTERRUPT_RISING_EDGE,
    "FALLING": gpio_ns.INTERRUPT_FALLING_EDGE,
    "ANY": gpio_ns.INTERRUPT_ANY_EDGE,
}

CONF_GATE_PIN = "gate_pin"
CONF_ZERO_CROSS_PIN = "zero_cross_pin"
CONF_INIT_WITH_HALF_CYCLE = "init_with_half_cycle"
CONF_ZERO_CROSS_INTERRUPT_TYPE = "zero_cross_interrupt_type"

CONFIG_SCHEMA = cv.All(
    output.FLOAT_OUTPUT_SCHEMA.extend(
        {
            cv.Required(CONF_ID): cv.declare_id(AcDimmer),
            cv.Required(CONF_GATE_PIN): pins.internal_gpio_output_pin_schema,
            cv.Required(CONF_ZERO_CROSS_PIN): pins.internal_gpio_input_pin_schema,
            cv.Optional(CONF_ZERO_CROSS_INTERRUPT_TYPE, default="FALLING"): cv.enum(
                ZC_INTERRUPT_TYPES, upper=True, space="_"
            ),
            cv.Optional(CONF_INIT_WITH_HALF_CYCLE, default=True): cv.boolean,
            cv.Optional(CONF_METHOD, default="leading pulse"): cv.enum(
                DIM_METHODS, upper=True, space="_"
            ),
        }
    ).extend(cv.COMPONENT_SCHEMA),
)


def _uses_bk72xx_timer() -> bool:
    # The BK7231Q SDK registers no timer driver: there the dimmer stays on / off only
    return CORE.is_bk72xx and get_libretiny_family() != FAMILY_BK7231Q


def _final_validate(config: ConfigType) -> ConfigType:
    if not _uses_bk72xx_timer():
        return config
    full_config = fv.full_config.get()
    # The dimmer timer is BKTIMER1, which these use too
    if any(
        receiver.get("sampling") == "timer"
        for receiver in full_config.get("remote_receiver", [])
    ):
        raise cv.Invalid(
            "ac_dimmer and remote_receiver's 'sampling: timer' both use BKTIMER1"
        )
    if get_libretiny_family() == FAMILY_BK7238 and "remote_transmitter" in full_config:
        raise cv.Invalid(
            f"ac_dimmer and remote_transmitter both use BKTIMER1 on {FAMILY_BK7238}"
        )
    return config


FINAL_VALIDATE_SCHEMA = _final_validate


async def to_code(config: ConfigType) -> None:
    if CORE.is_esp32:
        from esphome.components.esp32 import include_builtin_idf_component

        # Re-enable the gptimer driver (excluded by default to save compile time)
        include_builtin_idf_component("esp_driver_gptimer")
    elif _uses_bk72xx_timer():
        cg.add_define("USE_AC_DIMMER_BK72XX_TIMER")

    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    # override default min power to 10%
    if CONF_MIN_POWER not in config:
        config[CONF_MIN_POWER] = 0.1
    await output.register_output(var, config)

    await cg.add_pin(var.set_gate_pin, config[CONF_GATE_PIN])
    await cg.add_pin(var.set_zero_cross_pin, config[CONF_ZERO_CROSS_PIN])
    cg.add(var.set_zero_cross_interrupt_type(config[CONF_ZERO_CROSS_INTERRUPT_TYPE]))
    cg.add(var.set_init_with_half_cycle(config[CONF_INIT_WITH_HALF_CYCLE]))
    cg.add(var.set_method(config[CONF_METHOD]))
