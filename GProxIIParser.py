from contextlib import ExitStack
import os
"""
GProx Data

XORVALUE = The 10 Bit XOR Value Key we are trying to find.
WWWWWW = 6 Bit Wiegand Length, either 26, 36 or 40
LLLLLLLLLLLLLLLL = 16 Bit Lock code. Either 1000000000000000 (US) or 0110111100000110 (NZ/Chubb). This is hard-programmed to the reader. The reader will only accept tags with the same lock code. 
DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD = 40 Bits Wiegand Data. In reverse byte order when received via D0/D1 GPIO pins for successful tag based on Wiegand length.

"""
filename = "GProxIIDataSet"
delimit = ' '  # Main delimiter
# delimit = ',`'
second_delmit = ''  # Second delimiter if we want to break up the xor code
# second_delmit = ','

# Config options
config_wg_lc_as_int = False
config_print_footers = False

# Data is split into length and lock codes
filenames = {'26-0': 0, '36-0': 0, '40-0': 0, '26-1': 0, '36-1': 0, '40-1': 0}

# Wiegand lengths
wiegand_lengths = ['010110', '001001', '000101']
# Two different lock codes observed.
lock_codes = ['1000000000000000', '0110111100000110']


def strip_parity(input_bin, n):
    """
    Strip zero parity from binary string

    Args:
        input_bin: Binary string
        n: zero bit check digit to remove
    Returns: Binary string without check digits
    """
    if int("".join([input_bin[i+n-1] for i in range(0, len(input_bin), n)]), 2) == 0:
        return "".join([input_bin[i:i+n-1] for i in range(0, len(input_bin), n)])
    else:
        print('Invalid check digits, should be all zeros')
        exit(0)


def reverse_bits(input_bin):
    # Reverse 8 bits per byte in the binary string
    return "".join([input_bin[i:i+8][::-1] for i in range(0, len(input_bin), 8)])


def xor_string(input_bin):
    # XOR the string in bytes using the first 8 bits of the string as the XOR Key.
    xor_key = int(input_bin[0:8], 2)
    hex_bytes = [int(input_bin[i:i+8], 2) for i in range(0, len(input_bin), 8)]
    for i in range(1, 9):
        hex_bytes[i] = xor_key ^ hex_bytes[i]
    return "".join([f"{hex_bytes[i]:0>8b}" for i in range(0, len(hex_bytes))])


def convert_hex(input_hex):
    """
    Main conversion function to take hex string and convert it to non-xored binary string

    Args:
        input_hex: 12 byte hex string from GProxII Tag

    Returns: List binary values converted into reverse bit int values for sorting later
    - 10 bit key
    - 6 bit Wiegand length
    - 16 bit lock code
    - 40 bit Wiegand data split into 4 groups of 10 bits
    - 40 bit Wiegand data as a single int
    """

    input_binary_string = format(int(input_hex, 16), "096b")  # Convert to binary string
    if input_binary_string[:6] == "111110":  # Check header
        # Convert the source 12 bytes into 9 bytes and xor value
        binary_string = input_binary_string[6:]  # Strip header
        binary_string = strip_parity(binary_string, 5)  # Strip 5th bit of zero parity to make 9 bytes
        binary_xor = xor_string(binary_string)  # XOR string using first byte

        # Split out the binary string into key, wiegand length, lock code and wiegand data
        bin_key = binary_xor[0:10]
        bin_wiegand_length = binary_xor[10:16]
        bin_lock_code = binary_xor[16:32]
        bin_wiegand_data = binary_xor[32:]

        # Split the wiegand data into groups based on length
        w_d_split_len = 10
        w_d_split = [bin_wiegand_data[i:i + w_d_split_len] for i in range(0, 40, w_d_split_len)]
        w_d_split_joined = " ".join(w_d_split)

        # Find values that have the same repeat key value in the list by converting it to a set
        key_int = 0
        if len(list(set(w_d_split))) == 2 and '0000000000' in list(set(w_d_split)):
            key_int = list(set(w_d_split))[0] if list(set(w_d_split))[1] == '0000000000' else list(set(w_d_split))[1]

        # Build a final binary string of everything including the grouping
        # final_split = f'{bin_key} {bin_wiegand_length} {bin_lock_code} {w_d_split_joined} {key_int} {bin_wiegand_data}'.split(' ')

        # Convert to reverse bit decimal numbers
        final_split = f'{bin_key} {bin_wiegand_length} {bin_lock_code} {w_d_split_joined} {key_int} {bin_wiegand_data}'.split(' ')
        final_split = [int(i[::-1], 2) for i in final_split]

        return final_split
    else:
        print(F'Bad Record: {input_hex}')
        exit(0)


# List for missing keys removing found keys during file parsing
missing_keys = {}
for key in filenames.keys():
    missing_keys[key] = [i for i in range(0, 1023)]

dataset = []

# Open input csv file
with (open(f'{filename}.csv') as input_file):
    for line in input_file:
        if len(line) > 3:
            current_line = line.upper().rstrip().replace(',', ' ').split(' ')
            hex_string = current_line[0]
            if len(hex_string) == 24 and hex_string[0] == 'F':
                # wc_key, w_len, w_lc, w_d = convert_hex(hex_string)
                convert_result = convert_hex(hex_string)

                # Only bring across the WG40 LC1 entries
                # if convert_result[1] == 40 and convert_result[2] == 1:
                #     dataset.append(convert_result)

                # Append converted dataset into list
                dataset.append(convert_result)


# Sort output dataset by matching key values and integers
sorted_dataset = sorted(dataset, key=lambda x: (x[1], x[2], x[7], x[8]))

# Sort output dataset by checksum and integer
# sorted_dataset = sorted(dataset, key=lambda x: (x[1], x[2], x[0], x[8]))

# Create output files
with (ExitStack() as stack):
    files = [stack.enter_context(open(f"{filename}-{fname}.csv", 'w')) for fname in filenames.keys()]
# with (open(f'{filename}-output.csv', 'w') as output_file):
    last_key = 0
    for i in sorted_dataset:

        # Match the lock code value if it is a decimal number, or if it is a binary string
        if isinstance(i[1], int):
            wg_len = i[1]
        else:
            wg_len = int(i[1][::-1], 2)

        # Match the lock code value if it is a decimal number, or if it is a binary string
        if isinstance(i[2], int):
            wg_lc = lock_codes.index(f'{i[2]:016b}'[::-1])
        else:
            wg_lc = lock_codes.index(i[2])
        wg_len_lc = f'{wg_len}-{wg_lc}'

        # Print header grouping
        if config_print_footers and last_key != 0 and i[7] != last_key:
            files[list(filenames.keys()).index(wg_len_lc)].writelines(f'{last_key:10d}\n\n')
        #     last_key_dec = last_key
        #     # if isinstance(last_key[0], int) else i[0]

        bin_key = f'{i[0]:010b}'[::-1] if isinstance(i[0], int) else i[0]

        bin_wiegand_length = i[1] if config_wg_lc_as_int else f'{i[1]:06b}'[::-1]
        bin_lock_code = i[2] if config_wg_lc_as_int else f'{i[2]:06b}'[::-1]

        bin_array = " ".join([f'{i[j]:010b}'[::-1] if isinstance(i[j], int) else i[j] for j in range(3, 8)])
        wiegand_int = i[8]

        # Gap between sorted values
        if config_print_footers and last_key == 0 and i[7] == 1:
            files[list(filenames.keys()).index(wg_len_lc)].writelines('\n')

        if config_print_footers:
            files[list(filenames.keys()).index(wg_len_lc)].writelines(f'{bin_key} {bin_wiegand_length} {bin_lock_code} {bin_array} {wiegand_int}' +'\n')
        else:
            files[list(filenames.keys()).index(wg_len_lc)].writelines(f'{bin_key} {bin_wiegand_length} {bin_lock_code} {bin_array}' +'\n')

        last_key = i[7]
