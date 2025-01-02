# Understanding GProxII Card Data

Reverse engineering the 10 bit crc checksum or algorithm that is used on the GProxII tags.

This has involved brute forcing a lot of numbers with a flipper zero and a GProxII reader to emulate the whole 10 bit key space where one value is correct. Thankfully the GProxII readers don't have any anti-hammering logic so it will happily accept millions of numbers and not lock up.

## Underlying known facts about the tags 

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

## Bit/Byte breakdown

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

- The XOR does happen against the first two bits from the XOR value to the last 2 bits of the XOR value in byte 1. IE the XOR CODE AABBCCDDEE, the bits AA and EE are XORed and the calculation takes that into account when the value is stored.

- The calculation doesn't use the reverse bytes. As when you don't reverse the bytes, it's the first 10 bits that are the key.

- There are many sequences / patterns in 10 bit in the Wiegand data so the key calculation is assumed to either be 5 bit or 10 bit.

# Example Data and patterns

The examples are mostly against the WG40-LC0 as that uses the whole 40 bits of wiegand numbering and the LC0 reader I had with Lock Code 1 was easier to modify. What I also noticed is when using a WG26/WG36 and brute forcing numbers outside the number space such as from bit 27 to 40 on a WG26 then the reader would beep as if it was a correct value, but the GPIO value would be scrambled and neither a truncated 26 bit value or the full value sent.

Starting with WG Bit 1 and taking 10 bit numbers you can see that 
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
{'IntValue': 1, 'EntryCount': 16, 'Keys': 8, '40-0-1100010100': 2, '40-0-1101101110': 2, '40-0-0100010100': 2, '40-0-1100100110': 2, '40-0-0101011100': 2, '40-0-0100100110': 2, '40-0-1101011100': 2, '40-0-0101101110': 1}
```



## Missing checksums and numbers.

With LC0 there are some checksum values that never seemed to be calculated. To me this indicates that the checksum is a 5 bit key where the higher 5 bits are a separate calculation to the lower 5 bits and is used from the first 22 bits from the WG Length and the Lock Code.
For the LC1 tags when brute forcing them I did find every checksum value.

```
LC0 - WG26 ['1010100000', '0100010000', '1010101000', '1010100100', '1010110100', '1110110100', '0001101100', '1001101100', '0000000010', '1111000010', '1100100010', '1010100010', '0100110010', '1010101010', '1001101010', '1101111010', '0011111010', '1010100110', '1001001110', '1001101110', '1010100001', '1001100001', '1001001001', '1010101001', '0000011001', '1000011001', '1100011001', '1110000101', '1010100101', '0111001101', '0101000011', '1010100011', '0101010011', '1010101011', '1010100111', '1011100111']
LC0 - WG36 ['1010100000', '1010101000', '1010100100', '1010000010', '1010100010', '1010101010', '1010100110', '1010100001', '1010101001', '1010100101', '1010100011', '1010101011', '1010100111']
LC0 - WG40  ['1010100000', '1010101000', '1010100100', '1010100010', '1010101010', '1010100110', '1010100001', '1010101001', '1010100101', '1010100011', '1010101011', '1010100111']
LC1 - WG26 []
LC1 - WG36 []
LC1 - WG40 []
```
