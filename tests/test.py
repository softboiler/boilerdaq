import boilerdaq as daq

# def loop():
#     while _do_plot:
#         time_read, readings = read_sensors(sensors, delay)
#         csv_write_results(
#             results_raw_path, raw_fieldnames, time_read, readings
#         )

#         rand = readings[0].value

#         readings = calibrate_readings(readings)
#         fluxes = get_fluxes(readings, flux_params)
#         csv_write_results(
#             RESULTS_CAL_PATH,
#             cal_fieldnames,
#             time_read,
#             readings + fluxes,
#         )

#         _plot_cache.append(rand)


# def plot_loop():
#     _curve.setData(_plot_cache)


sensors_path = "config/sensors.csv"
flux_params_path = "config/flux_params.csv"
results_raw_path = "results/results_raw.csv"
results_cal_path = "results/results_cal.csv"
plot_cache_length = 100
delay = 0.5

# loop setup
sensors = daq.csv_read_sensors(sensors_path)
flux_params = daq.csv_read_flux_params(flux_params_path, sensors)

time_read, readings = daq.read_sensors(sensors, delay)
results_raw_path, raw_fieldnames = daq.csv_create_results(
    results_raw_path, time_read, readings
)

readings = daq.calibrate_readings(readings)
fluxes = daq.get_fluxes(readings, flux_params)
results_cal_path, cal_fieldnames = daq.csv_create_results(
    results_cal_path, time_read, readings + fluxes
)

values = [reading.value for reading in readings]
pressure = values[9]

# _do_plot = True
# _plot_cache = deque([pressure], maxlen=PLOT_CACHE_LENGTH)

# # loop start in background
# thread = Thread(target=loop)
# thread.daemon = True
# thread.start()

# # plot loop setup
# win = pyqtgraph.GraphicsWindow()
# win.setWindowTitle("")
# pyqtgraph.setConfigOption("foreground", "w")

# plot = win.addPlot(title="")
# line = pyqtgraph.mkPen((0, 255, 0), width=1)
# plot.addLegend(offset=(10, 5))

# _curve = plot.plot(_plot_cache, pen=line, name="",)

# plot.setRange(yRange=[0, 1])
# plot.setLabel(
#     "bottom", text="",
# )
# plot.showGrid(x=True, y=False)

# # plot loop start
# timer = pyqtgraph.QtCore.QTimer()
# timer.timeout.connect(plot_loop)
# timer.start(0)

# pyqtgraph.Qt.QtGui.QApplication.instance().exec_()
# _do_plot = False
