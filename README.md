# Understanding GProxII Card Data

Reverse engineering the 10 bit crc checksum or algorithm that is used on the GProxII tags.

This has involved brute forcing a lot of numbers with a flipper zero and a GProxII reader to emulate the whole 10 bit key space where one value is correct. Thankfully the GProxII readers don't have any anti-hammering logic so it will happily accept millions of numbers and not lock up.

# Test Hardware

I have 3 readers and two flipper zero's to test with.
- 120-6434 - LockCode 1 - Verex Mini reader 
- 111-8284 - LockCode 1 - Guardall GProx II Switchplate Reader Keypad - https://fccid.io/X78MU2A
- 111-8266 - LockCode 24822(NZ) - Guardall GProx II Mullion Reader Keypad - https://fccid.io/X78SP2M

I have written flipper zero code that emulates the whole 10 bit key space. It emulates and turns the RFID field with the tag for 360ms and then turns the RFID field off for 120ms. If the checksum is correct then the reader beeps, then GPIOs that are also connected to the Flippper on A4/A7 trigger trigger. Then I save the valid key sent to a CSV on the SD card on the Flipper and progress to the next number. It takes approximately 8 minutes to bruteforce a single number depending on where it is in the checksum range.

# Underlying known facts about the tags 

Low frequency 125Mhz T5577 tags.

Block 0 either 
 - 00150060 (most common)
 - F0150060 (seen on NZ tags)

```
[=] --- T55x7 Configuration & Information ---------
[=]  Safer key                 : 0 (or 15 if block 0 = F0150060)
[=]  reserved                  : 0
[=]  Data bit rate             : 5 - RF/64
[=]  eXtended mode             : No
[=]  Modulation                : 16 - Biphase
[=]  PSK clock frequency       : 0 - RF/2
[=]  AOR - Answer on Request   : No
[=]  OTP - One Time Pad        : No
[=]  Max block                 : 3
[=]  Password mode             : No
[=]  Sequence Terminator       : No
[=]  Fast Write                : No
[=]  Inverse data              : No
[=]  POR-Delay                 : No
[=] -------------------------------------------------------------
[=]  Raw Data - Page 0, block 0
[=]  00150060
[=] --- Fingerprint ------------
[+] Config block match        : Guard Prox II
```

- 12 bytes / 96 bit raw key stored in blocks 1/2/3

- 6 bit preable of 111110

- 5 bit 0 bit parity check (so 5th bit is always 0) to strip out leaving 9 bytes / 72 bit payload.

- 10 bit key / checksum comprised of 8 bits used as XOR key in byte 0, and 2 bits in byte as a calculated value. <- This is what we are trying to figure out!

# Bit/Byte breakdown

```
Example Data:
F956D7356559565595655956
As binary string, showing 6 bit preamble and then 5 zero bit check value 
111110 01010 10110 11010 11100 11010 10110 01010 10110 01010 10110 01010 10110 01010 10110 01010 10110 01010 10110
Binary string without preamble and 5th check bit removed in 8 bit groups
01011011 11011110 11011011 01011011 01011011 01011011 01011011 01011011 01011011
Post XOR from first 8 bits
01011011 10000101 10000000 00000000 00000000 00000000 00000000 00000000 00000000
XORCode    WGLen  Lock Code        WGData
0101101110 000101 1000000000000000 0000000000 0000000000 0000000000 0000000000
```

- 10 Bit key / checksum consists of 8 bits from byte 0, and first two 2 bits from byte 1 as the assumption is the checksum is caculated on the linear bits

- byte 0 used as XOR key across remaining 8 bytes

- byte 1 first two bits are calculated and part of calculated key / checksum 10 bit value. Remaining 6 bits is the wiegand length LSB little endian - 3 known wiegand lengths. 26 (010110), 36 (001001) and 40 (000101). It is assumed that the 2 bits that are used in the checksum are post XOR.

- byte 2 and 3 is 16 bit lock code LSB little endian. US / International = 1 = 1000000000000000 which I refer to LC0 for brevity and Chubb / New Zealand = 24822 = 0110111100000110 which I refer to LC1

The lock code means if the reader will accept a valid tag or not. Testing with two readers one with lock code 1 and the other with lock code 24822. The reader would not accept any brute forced number space if the lock code did not match. There is a "programming card" which I have not got access to that can re-program the reader on startup to be locked to the particular lock code.

Assumed little endian 16 bit as reading the manual: https://fcc.report/FCC-ID/X78SP1M/1346318.pdf it mentions "lock code 1" as the default value. This is the most common datatype observed.

```
- Key / Lock Code: A "lock code" can prevent a dealer from attempting to take over another dealer’s customer. If a dealer orders a G-Prox II system to produce cards, add readers to their customer base, they can receive these parts:
• Generic Software
• A Desktop Card Programmer
• Blank Access Cards
• G-Prox II Readers
• A unique License Number
When the unique license number is entered into the software, it will program in an exclusive "lock code" if it was ordered. When a reader configuration card is programmed, this unique lock code will be transferred to it. When readers are programmed with the configuration card, their default lock code of "1" will be changed to a unique one. When user cards are programmed, the same unique lock code will be transferred to them. Matching lock codes at a location are necessary to unlock doors. WARNING: A configuration card with a different lock code, such as another dealer's lock code, can not be used to program G-Prox II readers at a location that does not use the same lock code. During the first 15 minutes that a G-Prox II reader is powered, the configuration card is applied to the reader to program it with e.g. the lock code. The lock code can only be programmed ONCE. De- and repowering the reader to re-start the 15 minute reader programming period to reapply a configuration card with a correctly matching lock code will not change the lock code. The reader will have to be returned to the Factory for the lock code to be re-set. User cards can not be programmed for a location with software that does not use the same lock code.
```

Importand line: 'their default lock code of "1" will be changed'

- bytes 4,5,6,7. The Wiegand data sent in reverse byte order via GPIOs D0/D1 based on the Wiegand length. If 26 bit then only the first reversed 26 bits are sent. Even though remaining bits can be set and are used in the key calculation they are not sent via D0/D1 GPIOs

# Checksum information

- The calculated value uses the full 62 bits from Wiegand Length (6) + Lock Code (16) + Wiegand Data (40)
- So when different Wiegand lengths or lock codes are used the checksum value is compeltely different.

# Assumptions

- The XOR does happen against the first two bits from the XOR value to the last 2 bits of the XOR value in byte 1. IE the XOR CODE AABBCCDDEE, the bits AA and EE are XORed and the calculation takes that into account when the value is stored. Thus the checksum for bits 0 and 1 of byte 1 needs to be XORed from the first two bits 

- The calculation doesn't use the reverse bytes. As when you don't reverse the bytes, it's the first 10 bits that are the key.

- The checksum calculation is 10 bit, as when bruteforcing XORing in sequence there is no repeating XOR values from 0 - 1023. This is repeated so far with the higher groups I have bruteforced but may not always be the case.

# Understanding the data

In an effort to be consistent the data is always sourced as the 12 bytes of source data in hex. This is parsed into the target data files.
** Note 
Main data file: `GProxIIDataSet.csv`
 - There are some duplicates in there with bad checksum numbers in the file `GProxIIDataSet.csv` As sometimes the GPIO pins fire even though nothing has changed. So therefor the flipper assumes that the number is correct when it actually isn't. I am progressively working through the file to ensure it's all correct and removing the bad entry from the main file.

The groups of decoded data and the numerical representation of the card number.

- 10 Bit key / checksum consists of 8 bits from byte 0, and first two 2 bits from byte 1 as the assumption is the checksum is caculated on the linear bits

- byte 0 used as XOR key across remaining 8 bytes

- byte 1 first two bits are calculated and part of calculated key / checksum 10 bit value. Remaining 6 bits is the wiegand length LSB little endian - 3 known wiegand lengths. 26 (010110), 36 (001001) and 40 (000101). It is assumed that the 2 bits that are used in the checksum are post XOR.

- byte 2 and 3 is 16 bit lock code LSB little endian. US / International = 1 = 1000000000000000 which I refer to LC0 for brevity and Chubb / New Zealand = 24822 = 0110111100000110 which I refer to LC1

The lock code means if the reader will accept a valid tag or not. Testing with two readers one with lock code 1 and the other with lock code 24822. The reader would not accept any brute forced number space if the lock code did not match. There is a "programming card" which I have not got access to but am still working on that.

# Checked and valid data

Checked data subset: `Checked-40-0_0-4095.csv`
 - Working through the above file I decided to pivot and bruteforce sequential numbers in the WC:40 space from 0 - 4095. This has shown some interesting outcomes.
 - For every 1024 bit range there is only a single unique checksum value. That applies 0-1023, 1024-2047, 2048-3071 and 3072 to 4095.
 - Bit 11 seems to be a XOR bit against bit 0 of the checksum.

```
F956D7356559565595655956 0101101110 000101 1000000000000000 0000000000 0000000000 0000000000 0000000000 0 40 474
FB5657156D5B56F5B56D5B56 1101101110 000101 1000000000000000 0000000000 1000000000 0000000000 0000000000 1024 40 475
F84613246118460184611846 0001001100 000101 1000000000000000 0000000000 0100000000 0000000000 0000000000 2048 40 200
FA469304691A46A1A4691A46 1001001100 000101 1000000000000000 0000000000 1100000000 0000000000 0000000000 3072 40 201

FB0AC010AC290AC2B0AC2B0A 1100010100 000101 1000000000000000 1000000000 0000000000 0000000000 0000000000 1 40 163
F90A4030A42B0A6290A4290A 0100010100 000101 1000000000000000 1000000000 1000000000 0000000000 0000000000 1025 40 162
FA1A4401A8681A96A1A86A1A 1000110111 000101 1000000000000000 1000000000 0100000000 0000000000 0000000000 2049 40 945
F81AC421A06A1A3681A0681A 0000110111 000101 1000000000000000 1000000000 1100000000 0000000000 0000000000 3073 40 944

F88663286219586188621886 0010001101 000101 1000000000000000 0111111101 0000000000 0000000000 0000000000 766 40 708
FA86E3086A1B58C1A86A1A86 1010001101 000101 1000000000000000 0111111101 1000000000 0000000000 0000000000 1790 40 709
F996E7396658483599665996 0110101110 000101 1000000000000000 0111111101 0100000000 0000000000 0000000000 2814 40 470
FB9667196E5A4895B96E5B96 1110101110 000101 1000000000000000 0111111101 1100000000 0000000000 0000000000 3838 40 471

FAC0F28C0B011EF02C0B02C0 1011000001 000101 1000000000000000 1111111101 0000000000 0000000000 0000000000 767 40 525
F8C072AC03031E500C0300C0 0011000001 000101 1000000000000000 1111111101 1000000000 0000000000 0000000000 1791 40 524
FBD0B69D0F400EA43D0F43D0 1111100001 000101 1000000000000000 1111111101 0100000000 0000000000 0000000000 2815 40 543
F9D036BD07420E041D0741D0 0111100001 000101 1000000000000000 1111111101 1100000000 0000000000 0000000000 3839 40 542

Stops matching on first pair (0-2048), but still matches (2048 - 4096)

F89A6429A2689AE689A2689A 0010110101 000101 1000000000000000 0000000011 0000000000 0000000000 0000000000 768 40 692
FA8663086A1A8641A86A1A86 1010001111 000101 1000000000000000 0000000011 1000000000 0000000000 0000000000 1792 40 965
F94693346519468194651946 0101001111 000101 1000000000000000 0000000011 0100000000 0000000000 0000000000 2816 40 970
FB4613146D1B4621B46D1B46 1101001111 000101 1000000000000000 0000000011 1100000000 0000000000 0000000000 3840 40 971

FADEF50DEB78DE77ADEB7ADE 1011111101 000101 1000000000000000 1000000011 0000000000 0000000000 0000000000 769 40 765
F8C0F2AC0302C0D00C0300C0 0011000011 000101 1000000000000000 1000000011 1000000000 0000000000 0000000000 1793 40 780
FB1AC411AC691A16B1AC6B1A 1100110100 000101 1000000000000000 1000000011 0100000000 0000000000 0000000000 2817 40 179
F91A4431A46B1AB691A4691A 0100110100 000101 1000000000000000 1000000011 1100000000 0000000000 0000000000 3841 40 178

Matches on first pair (0-2048) but doesn't match on second pair (2048 - 4096)

F95617356558569595655956 0101101101 000101 1000000000000000 0100000011 0000000000 0000000000 0000000000 770 40 730
FB5697156D5A5635B56D5B56 1101101101 000101 1000000000000000 0100000011 1000000000 0000000000 0000000000 1794 40 731
F88AE028A2298AF288A2288A 0010010111 000101 1000000000000000 0100000011 0100000000 0000000000 0000000000 2818 40 932
FA96A7096A5B9655A96A5A96 1010101100 000101 1000000000000000 0100000011 1100000000 0000000000 0000000000 3842 40 213

FB0202102C080200B02C0B02 1100000111 000101 1000000000000000 1100000011 0000000000 0000000000 0000000000 771 40 899
F9028230240A02A090240902 0100000111 000101 1000000000000000 1100000011 1000000000 0000000000 0000000000 1795 40 898
FAC0728C0B01C0602C0B02C0 1011000011 000101 1000000000000000 1100000011 0100000000 0000000000 0000000000 2819 40 781
F8DE752DE37BDEC78DE378DE 0011111101 000101 1000000000000000 1100000011 1100000000 0000000000 0000000000 3843 40 764
```

# Other observations

## Missing checksums with new reader (120-6434).

With the newer reader (120-6434) which I have used most of the time which is LC0 there are some checksum values that the newer reader will just not accept. Further testing with the old reader (111-8284) has shown that the old model reader *does* accept the checksums but exactly the same value will never be accepted by the newer model.

The checksums are:

```
1010100000
1010100001
1010100010
1010100011

1010100100
1010100101
1010100110
1010100111

1010101000
1010101001
1010101010
1010101011
```

## There are repeating XORs between groups

Starting with WG Bit 1 and taking 10 bit numbers you can see that certain checksums are repeating, so this leads me to believe it is a 10 or 20 bit calculation.

```
1100010100 000101 1000000000000000 1000000000 0000000000 0000000000 0000000000 0000000000001
1101101110 000101 1000000000000000 0000000000 1000000000 0000000000 0000000000 0000000001024
0100010100 000101 1000000000000000 1000000000 1000000000 0000000000 0000000000 0000000001025
1100100110 000101 1000000000000000 0000000000 0000000000 1000000000 0000000000 0000001048576
0101011100 000101 1000000000000000 1000000000 0000000000 1000000000 0000000000 0000001048577
0100100110 000101 1000000000000000 0000000000 1000000000 1000000000 0000000000 0000001049600
1101011100 000101 1000000000000000 1000000000 1000000000 1000000000 0000000000 0000001049601
1101101110 000101 1000000000000000 0000000000 0000000000 0000000000 1000000000 0001073741824
0100010100 000101 1000000000000000 1000000000 0000000000 0000000000 1000000000 0001073741825
0101101110 000101 1000000000000000 0000000000 1000000000 0000000000 1000000000 0001073742848
1100010100 000101 1000000000000000 1000000000 1000000000 0000000000 1000000000 0001073742849
0100100110 000101 1000000000000000 0000000000 0000000000 1000000000 1000000000 0001074790400
1101011100 000101 1000000000000000 1000000000 0000000000 1000000000 1000000000 0001074790401
1100100110 000101 1000000000000000 0000000000 1000000000 1000000000 1000000000 0001074791424
0101011100 000101 1000000000000000 1000000000 1000000000 1000000000 1000000000 0001074791425
```
