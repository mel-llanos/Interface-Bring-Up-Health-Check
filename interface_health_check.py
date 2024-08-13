#!/usr/bin/python3

import syslog
import os
import re
import time
from cli import cli
from concurrent.futures import ThreadPoolExecutor, as_completed

# File to keep track of script execution count
count_file = '/bootflash/execution_count.txt'

# Define the range of interfaces to check (2 through 48)
interfaces = range(2, 49)

# Function to read the execution count from a file
def read_execution_count(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            content = file.read().strip()
            if content.isdigit():
                return int(content)
    return 0

# Function to write the execution count to a file
def write_execution_count(file_path, count):
    with open(file_path, 'w') as file:
        file.write(str(count))

# Function to parse ASIC counters for bad preamble
def check_asic_counter():
    command = f"slot 1 q \"sh ha int tah count asic 0\" | egrep -i \"REG_NAME.*M[0-9]|preamble\""
    output = cli(command)

    # Split the output into lines
    lines = output.strip().split('\n')

    # Initialize variables to store the current MAC instances and their corresponding values
    mac_instances = []
    values = []

    # List to store MAC instances with bad preambles
    bad_preamble_instances = []

    # Process each line
    for line in lines:
        if line.startswith("REG_NAME"):
            # Extract MAC instances
            mac_instances = re.findall(r'M\d+,\d+-\d+Gx?\d*', line)
            #print("MAC Instances:", mac_instances) # Print MAC instances
        elif "90-Rx Bad Preamble" in line:
            # Extract values by splitting the line into fixed-width fields
            # Remove the "90-Rx Bad Preamble" part and then split the rest
            values = line.split()[3:]  # Skip the first three elements which are "90-Rx", "Bad", and "Preamble"
            #print("Values:", values) # Print values
            # Check for any values that are not "...."
            for i, value in enumerate(values):
                if value != "....":
                    if re.match(r'M([0-9]|1[0-4]),', mac_instances[i]):
                        bad_preamble_instances.append(mac_instances[i])
    
    return bool(bad_preamble_instances), bad_preamble_instances

# Function to check CDP entry for an interface
def check_cdp_entry(interface):
    command = f"show cdp neighbors interface {interface} detail"
    output = cli(command)
    pattern = fr"Device ID:.*?Interface: {re.escape(interface)}, Port ID \(outgoing port\):"
    match = re.search(pattern, output, re.DOTALL)
    return bool(match)

# Function to get the second input rate from an interface
def get_input_rate(interface):
    command = f"show interface {interface}"
    output = cli(command)
    match = re.search(r'input rate \d+ bps.*?input rate (\d+) bps', output, re.DOTALL)
    if match:
        return int(match.group(1))
    else:
        print(f"Could not parse second input rate for {interface}.")
        return None

# Function to perform all checks for a single interface
def check_interface(i):
    interface = f"Ethernet1/{i}"
    
    # Check CDP entry
    has_cdp_entry = check_cdp_entry(interface)
    
    # Check input rates three times
    rates = []
    for _ in range(3):
        rate = get_input_rate(interface)
        if rate is not None:
            rates.append(rate)
        time.sleep(1)  # Wait for 1 second before the next reading
    
    # Check if the interface has no CDP entry & input rate is 0 bps consistently
    if not has_cdp_entry and all(rate == 0 for rate in rates):
        return True
    return False

# Main function to run the checks for each interface
def main():
    # Read the current execution count
    execution_count = read_execution_count(count_file)
    execution_count += 1
    write_execution_count(count_file, execution_count)
    
    issue_detected = False
    
    time.sleep(15)

    # Use ThreadPoolExecutor to run checks concurrently
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(check_interface, i) for i in interfaces]
        for future in as_completed(futures):
            if future.result():
                issue_detected = True
    
    # Check ASIC counter for bad preamble
    bad_preamble_found, bad_preamble_instances = check_asic_counter()

    if issue_detected or bad_preamble_found:
        syslog.syslog(syslog.LOG_CRIT, f'Issue detected on execution #{execution_count}')
        if bad_preamble_found:
            for instance in bad_preamble_instances:
                syslog.syslog(syslog.LOG_CRIT, f'Bad preamble found in MAC instance: {instance}')
    else:
        syslog.syslog(syslog.LOG_INFO, f'No issue detected on execution #{execution_count}')
        # Execute write erase and reload commands
        try:
            cli('write erase')
            cli('reload')
        except Exception as e:
            syslog.syslog(syslog.LOG_ERR, f'Failed to execute write erase or reload: {e}')

if __name__ == "__main__":
    main()
