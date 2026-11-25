#include "hw_timer_bk72xx.h"

// clang-tidy cannot parse the Beken SDK headers pulled in via ArduinoPrivate.h
#if defined(USE_AC_DIMMER_BK72XX_TIMER) && !defined(CLANG_TIDY)

// ArduinoPrivate.h = Arduino.h + the BDK SDK headers (bk_timer.h, bk_timer_pub.h, sys_config.h)
#include <ArduinoPrivate.h>

extern "C" {
#include "fake_clock_pub.h"
}

// The FreeRTOS tick runs on BKTIMER0 only with LT_MICROS_HIGH_RES, the default everywhere but on the BK7231Q,
// which config validation rejects.
#if !defined(LT_MICROS_HIGH_RES) || !LT_MICROS_HIGH_RES
#error "ac_dimmer needs LT_MICROS_HIGH_RES"
#endif

namespace esphome::ac_dimmer {

// BKTIMER0 is the FreeRTOS tick and BKTIMER2 the SDK clock calibration. remote_receiver's timer sampling and
// remote_transmitter on BK7238 use BKTIMER1 too, which config validation rejects.
static constexpr uint8_t DIMMER_TIMER = BKTIMER1;

// LibreTiny's micros() keeps its state in statics that the main loop updates too, so an interrupt landing inside a
// micros() call of the main loop can be off by a whole tick, and a gate pulse that early is a visible flash. This
// clock reads the same counter, which runs at the crystal frequency and wraps every FCLK_DURATION_MS.
static constexpr uint32_t COUNTS_PER_US = CFG_XTAL_FREQUENCE / 1000000;
static constexpr uint32_t WRAP_US = FCLK_DURATION_MS * 1000;
// The latch completes in a few cycles; this bound only guards against a controller that never finishes the read
static constexpr uint32_t READ_SPINS = 100;

static uint32_t clock_base_us = 0;  // NOLINT(cppcoreguidelines-avoid-non-const-global-variables)
static uint32_t clock_last = 0;     // NOLINT(cppcoreguidelines-avoid-non-const-global-variables)

bool bk72xx_timer_begin(uint32_t interval_us, void (*isr)(uint8_t)) {
  timer_param_t param{};
  param.channel = DIMMER_TIMER;
  param.div = 1;
  param.period = interval_us;
  param.t_Int_Handler = isr;
  if (sddev_control((char *) TIMER_DEV_NAME, CMD_TIMER_INIT_PARAM_US, &param) != 0)
    return false;
  UINT32 channel = DIMMER_TIMER;
  return sddev_control((char *) TIMER_DEV_NAME, CMD_TIMER_UNIT_ENABLE, &channel) == 0;
}

bool bk72xx_clock_us(uint32_t *now) {
  // Index 0, the same read LibreTiny's micros() does, so a read of the main loop cannot pick up another timer's value
  REG_WRITE(TIMER0_2_READ_CTL, (BKTIMER0 << TIMER0_2_READ_INDEX_POSI) | TIMER0_2_READ_OP_BIT);
  for (uint32_t spins = 0; spins < READ_SPINS && (REG_READ(TIMER0_2_READ_CTL) & TIMER0_2_READ_OP_BIT); spins++) {
  }
  if (REG_READ(TIMER0_2_READ_CTL) & TIMER0_2_READ_OP_BIT)
    return false;
  const uint32_t count = REG_READ(TIMER0_2_READ_VALUE);
  if (count < clock_last)
    clock_base_us += WRAP_US;
  clock_last = count;
  *now = clock_base_us + count / COUNTS_PER_US;
  return true;
}

}  // namespace esphome::ac_dimmer

#endif  // USE_AC_DIMMER_BK72XX_TIMER && !CLANG_TIDY
