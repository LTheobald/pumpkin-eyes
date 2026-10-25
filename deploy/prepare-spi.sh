#!/bin/sh
# Pi 4 Garden workaround, tested manually by the owner. No boot-file edits.
set -eu
PATH=/usr/sbin:/usr/bin:/sbin:/bin
export PATH

if [ "$(id -u)" -ne 0 ]; then
    echo "Run this helper as root, before starting any SPI applications." >&2
    exit 1
fi

case "$(tr -d '\000' < /proc/device-tree/model)" in
    'Raspberry Pi 4 Model B'*) ;;
    *) echo "This workaround is intended for the confirmed Pi 4 Model B only." >&2; exit 1 ;;
esac

# /run is reset at boot. Avoid stacking overlays on repeated service starts.
if [ -f /run/pumpkin-spi.ready ]; then
    exit 0
fi

modprobe -r spi_bcm2835
# If applying the overlay fails, restore the driver before reporting failure.
if ! dtoverlay spi0-2cs no_miso; then
    modprobe spi_bcm2835
    exit 1
fi
modprobe spi_bcm2835
touch /run/pumpkin-spi.ready
echo "Pumpkin SPI prepared: GPIO9 excluded from SPI MISO."
