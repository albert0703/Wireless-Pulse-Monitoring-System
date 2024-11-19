import time
import threading
import numpy as np
from max30102 import MAX30102
import hrcalc
import bluetooth  # Import the bluetooth module


class HeartRateMonitor:
    
    LOOP_INTERVAL = 0.01  # Time interval between sensor readings in seconds

    def __init__(self, print_raw=False, print_result=True):
        self.bpm = 0
        self.print_raw = print_raw
        self.print_result = print_result
        self._thread = None
        self._bluetooth_socket = None  # Bluetooth socket attribute

        if self.print_raw:
            print('IR, Red')

    def start_sensor(self):
        # Initialize Bluetooth connection
        self._init_bluetooth()
        
        self._thread = threading.Thread(target=self._run_sensor)
        self._thread.stopped = False
        self._thread.start()

    def stop_sensor(self, timeout=2.0):
        if self._thread is not None:
            self._thread.stopped = True
            self.bpm = 0
            self._thread.join(timeout)
        # Close Bluetooth connection
        if self._bluetooth_socket:
            self._bluetooth_socket.close()

    def _init_bluetooth(self):
        server_mac_address = '2C:CF:67:03:09:B5'  # Replace with the MAC address of the receiver Raspberry Pi
        port = 1  # Port should match on both devices

        try:
            self._bluetooth_socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            self._bluetooth_socket.connect((server_mac_address, port))
            print("Bluetooth connection established.")
        except bluetooth.BluetoothError as e:
            print(f"Could not establish Bluetooth connection: {e}")
            self._bluetooth_socket = None

    def _run_sensor(self):
        sensor = MAX30102()
        ir_data_buffer = []
        red_data_buffer = []
        bpm_values = []

        try:
            while not self._thread.stopped:
                num_samples = sensor.get_data_present()
                if num_samples > 0:
                    # Read available samples from the sensor
                    for _ in range(num_samples):
                        red_sample, ir_sample = sensor.read_fifo()
                        ir_data_buffer.append(ir_sample)
                        red_data_buffer.append(red_sample)

                        if self.print_raw:
                            print(f"{ir_sample}, {red_sample}")

                    # Keep only the last 100 samples
                    if len(ir_data_buffer) > 100:
                        ir_data_buffer = ir_data_buffer[-100:]
                        red_data_buffer = red_data_buffer[-100:]

                    # Perform calculations when enough data is collected
                    if len(ir_data_buffer) == 100:
                        bpm, valid_bpm, spo2, valid_spo2 = hrcalc.calc_hr_and_spo2(
                            ir_data_buffer, red_data_buffer
                        )
                        if valid_bpm:
                            bpm_values.append(bpm)
                            if len(bpm_values) > 4:
                                bpm_values = bpm_values[-4:]  # Keep the last 4 BPM readings

                            self.bpm = np.mean(bpm_values)

                            # Detect if a finger is placed on the sensor
                            if (
                                np.mean(ir_data_buffer) < 50000
                                and np.mean(red_data_buffer) < 50000
                            ):
                                self.bpm = 0
                                if self.print_result:
                                    print("Finger not detected")
                                    # Optionally send a message indicating no finger detected
                                    self.send_bluetooth_data("Finger not detected")
                            else:
                                # Send data over Bluetooth
                                if self.print_result:
                                    if spo2 != -999:
                                        message = f"BPM: {self.bpm:.2f}, SpO2: {spo2}"
                                        print(message)
                                        self.send_bluetooth_data(message)
                time.sleep(self.LOOP_INTERVAL)
        finally:
            sensor.shutdown()

    def send_bluetooth_data(self, data):
        if self._bluetooth_socket:
            try:
                self._bluetooth_socket.send(data + '\n')  # Append newline character
            except bluetooth.BluetoothError as e:
                print(f"Error sending data over Bluetooth: {e}")
        else:
            print("Bluetooth socket is not connected.")

def main():

    print("Sensor starting...")
    hr_monitor = HeartRateMonitor(print_raw=False, print_result=True)
    hr_monitor.start_sensor()

    try:
        while True:
            time.sleep(1)  # Keep the main thread alive
    except KeyboardInterrupt:
        print("\nKeyboard interrupt detected, exiting...")
    finally:
        hr_monitor.stop_sensor()
        print("Sensor stopped!")

if __name__ == "__main__":
    main()
