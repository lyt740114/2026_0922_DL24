# DL24 Production ATE v6.0

## Hardware
- Use 4-pin Kelvin sensing for DL24 load wiring.
- Place the NTC probe firmly on the battery cell or hottest expected surface.
- Install the CH340 USB serial driver when Windows does not enumerate the adapter.

## Configuration
`test_config.json` contains current, cutoff voltage, temperature, rest duration, sampling interval, and DCIR settings.

## Distribution
The application stores configuration and CSV/PNG logs beside the executable. PyInstaller `--onefile` and `--onedir` deployments are supported.
