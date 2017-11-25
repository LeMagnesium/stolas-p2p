# Protocol Draft

### Important bits of info
 - Since `recv` does not care for the end of the packets we send (since it's a `SOCK_STREAM`, which rightfully contains the word 'stream'), this protocol must be respected in order for the clients to successfully slice and process all packages.
 - We do not use a '\0 at the end' kind of policy, which could lead to a lot of malicious payloads crashing our system if we don't design it carefully. This is a school project not the next BitTorrent.
 - The packet structures later described will use a cell per byte, which explains why some consecutive cells are marked with the same variable. However, variables of undefined size will only occupy one, but, in the reader's mind, should stretch appropriately.

## Protocol Summary

|Common Name|Hexadecimal Header|Signification|
|---|---|---|---|
|`HELLO`|`01`|Hello Byte which carries minimal peer information|
|`GOODBYE`|`02`|Goodbye Byte, indicates the imminent disconnection of the related peer|
|`SHAREPEER`|`03`|Share Peer, serves to expand the network by sharing available peer in connection circles|
|`REQUESTPEER`|`04`|Request that we get more peers from our immediate surroundings until we are sufficiently integrated in the network|
|`MESSAGE`|`05`|This is the message package which carries through the payload that will be interpreted by our message client|
|`MESSAGEACK`|`06`|Send the acknowledgement of a message|
|`MALFORMEDDATA`|`07`|Alert the peer that we received malformed data that cannot be safely interpreted and was therefore entirely scrapped. Any data sent before that and since the last response should be sent again|

### Hello
 - `u8 version`

|Packet Structure|
|---|
|`01`|`version`|


### GoodBye
|Packet Structure|
|---|
|`02`|

### Share Peer
 - `u8 af_inet` : If `4`, then the address is an IPv4 address (see 1st line), if `6`, it's a, IPv6 address (2nd line). Later, a `0` will indicate a domain name (NIY).
 - `u8 ip_addr[af_inet]` : Depending on the previous byte, a byte per byte encoded IP address.
 - `u16 port` : Listen port encoded on 2 bytes (0-65535)
 - `u8 domain_len` : If `af_inet` is `0`, then length of the domain name being shared.
 - `char domain[domain_len]` : Encoded domain name string.

|Packet Structure|
|---|
|`03`|`04`|`ip_addr[0]`|`ip_addr[1]`|`ip_addr[2]`|`ip_addr[3]`|`port`|`port`|
|`03`|`06`|`ip_addr[0]`|`ip_addr[1]`|`ip_addr[2]`|`ip_addr[3]`|`ip_addr[4]`|`ip_addr[5]`|`port`|`port`|
|`03`|`00`|`domain_len`|`domain`|

### Request Peer
|Packet Structure|
|---|
|`04`|

### Message packet
 - `u16 payload_len` : Length of the encoded payload placed after those two bytes
 - `u8 payload[payload_len]` : Encoded payload that's later interpreted by the message client
 - **Note**: A former version of this used one byte for `payload_len_len` and then grabbed `payload_len`. However, this meant a malicious client could overload a computer's memory by making it wait for `pow(2, 255)` bytes to arrive before slicing ; that's more bytes than there are atoms in the universe.

|Packet Structure|
|---|
|`05`|`payload_len`|`payload_len`|`payload`|

### Message Acknowledgement
|Packet Structure|
|---|
|`06`|

### Malformed Data
 - `u16 discarded_len` : Length of the discarded input buffer.

|Packet Structure|
|---|
|`07`|`discarded_len`|`discarded_len`|
