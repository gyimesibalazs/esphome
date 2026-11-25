#pragma once
#ifdef USE_AC_DIMMER_BK72XX_TIMER

#include <cstdint>

namespace esphome::ac_dimmer {

/// Starts BKTIMER1 with an interrupt every `interval_us`; false when the SDK refuses
bool bk72xx_timer_begin(uint32_t interval_us, void (*isr)(uint8_t));

/// The interrupts' clock in µs: BKTIMER0 (the RTOS tick timer) plus the wraps counted here. Call it only from the
/// GPIO and timer interrupts, and from the 50 µs timer interrupt every time, so that no wrap goes unseen. Returns
/// false when the counter could not be read.
bool bk72xx_clock_us(uint32_t *now);

}  // namespace esphome::ac_dimmer

#endif
