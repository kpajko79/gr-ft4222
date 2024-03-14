# gr-ft4222

IQ-over-SPI-to-USB source module for FT4222-based converters

## Description

This module implements a GNU Radio source block for FT4222-based SPI-to-USB
converters, enabling the reception of IQ samples sent over an SPI link.

The FT4222 is a multipurpose USB Hi-Speed to Multi-Channel Serial SPI/I2C
Master/Slave controller, manufactured by Future Technology Devices International
Limited (or FTDI Chip in short), who might be familiar for those who have used an
FT232H-based RS232/SPI/JTAG/anything adapter at least once in their life.

https://ftdichip.com/products/ft4222h/

The main difference between the FT232H and FT4222 is that the latter provides
a HIGH speed SPI DEVICE interface, which makes receiving high throughput streams
possible at a moderately low latency (even in python). The author was able to
test it with a 6.5 Mbps complex stream in MinGW running on Windows 7 (yeah)
on their lame X201 laptop...

The module has been tested with an official evaluation board available from FTDI:
https://ftdichip.com/products/umft4222ev/
But others should work too, or it should be straightforward to add support for them.
Another contender is https://bitwizard.nl/wiki/FT4222h, but was not tried.

## Configuration

The module is expected to be in DCNF1:DCNF0=00 mode, providing a serial and a
GPIO interface, so make sure to move the jumpers, in case yours is configured
differently. Otherwise the code could be modified to handle other configurations.

The chip supports only MSB order with an active-high chip select line.

The GPIO2 is driven as a #RESET (or nRESET if this looks more familiar) line
and shall be connected to your target board's reset input for providing some
form of synchronization.

## Installation

The implementation depends on the presence of the pyft4222 package, so before
installing, make sure that it's available on your system. It can be installed by:

pip install pyft4222

Or downloaded from:

https://github.com/lavovaLampa/pyft4222

## Required drivers and libraries

The pyft4222 driver in turn depends on the official FT4222 drivers and libraries
provided by FTDI and obtainable from their website:

https://ftdichip.com/drivers/d2xx-drivers/
https://ftdichip.com/software-examples/ft4222h-software-examples/

The libraries are included in pyft4222, but tend to be outdated.
