# Message Object documentation : V0x0

Messages are an important aspect of Stolas. The whole point of communication between peers is to send binary payloads wrapped around metadata.
A special class was created in `stolas/protocol.py` to represent those messages : `Message`. This document will focus on the different fields, methods, and the reasoning behind `Message`.

## Summary
 - Fields
   - `payload`
   - `channel`
   - `timestamp`
   - `usig` : 'Unique' Signature
   - `ttl` : Time To Live
 - Methods
   - Getters :
     - `get_payload() -> bytes`
     - `get_channel() -> str`
     - `get_timestamp() -> int`
     - `get_usig() -> bytes`
     - `get_ttl() -> int`
   - Setters :
     - `set_payload(bytes)`
     - `set_channel(str)`
     - `set_timestamp(int)`
     - `set_ttl(int)`
     - The constructor & its 'kwargs'
   - Conversion methods :
     - Implosion : class method from bytes
     - Explosion : conversion to binary blob
   - Control methods :
     - `is_alive` : Check alive-ness
     - `is_complete` : Check for missing fields
   - Implemented features :
     - Equality assertion
     - Non-equality assertion
     - String representation
     - Initialization

## Fields
The primary role of a message class instance is to carry with it the payload data of said message as well as its metadata.

### Payload
The payload is the main content of the message. For formatting facilitation, it is usually accepted that it is a sequence of bytes representing either a file or formatted HTML content. As such, our interface can use a WebEngine-like system to render the messages without the need for custom Markdown handling, or a complex system of our own (which would be catastrophically complex to code as we are not experts in anything remotely close to formatting).

### Channel
For now, the channel is a simple string (that may be empty) which describes a virtual "channel". You may (in the future) subscribe to channels in order to see their messages appear in the GUI's inbox. Users always receive all the messages they can and share all those they can as well, and the filtering only happens when Stolas' GUI is handed a new message object.
In the future, 'channel' may no longer refer to a simple string, but probably a set of cryptographic parameters tied to a string that serves the same purpose. Those cryptographic parameters may then help ensure that the message was emitted for the channel it describes. It is not a guarantee, as signing security will only come later in the project, and may affect other fields in order to protect everything (cf. `usig`).

### Timestamp
The timestamp is an integer which represents the emission time (at UTC) of the message in seconds from January 1st 1970 (using the Unix Timestamp standard). It it used to determine the emission moment, and, combined with the Time to Live, to determine whether we should keep broadcasting a message or scrap it already.

### Usig : 'Unique' Signature
The unique signature of a message is used to determine whether a message we receive is already stored in Stolas' message pile. Its prime purpose is to have a pseudo-uniqueness for temporary storage. It doesn't act as a check mark of integrity. In the future, the USIG may be used for integrity checking along with encryption systems.
For now, the USIG is the byte result of sha2-512 hashing of the text string made by concatenating the precise time of hashing, the MIN_INTEGRATION constant, the `repr` of kwargs, and a sample of 1 to 256 random bytes from u8 encoded in utf8.

### TTL : Time To Live
Messages cannot remain on the network forever, lest it becomes clogged and unusable. Much like how the foundational protocols of the web only allow packets in transit to live for a certain time, the protocol makes it so that each packet also carries an expiration time computed from its time of emission and a parameter given by the sender. The time to live is the duration during which the packet may proliferate within the network before being filtered out and cleaned out of network exchanges and active message piles.

## Methods

### Getters

All the getters take an implicit "self" reference for first and only argument.

| Name | Return Type | Description |
|-|---|
|get_payload | bytes | Returns the binary payload carried by the message. |
|get_channel | str | Returns the string describing the message's channel. |
|get_timestamp | int | Returns the integer representing the emission time in seconds elapsed since Epoch|
|get_usig | bytes | Returns the message's (hopefully) unique message signature. |
|get_ttl | int | Returns the time to live of the messasge in seconds. |

### Setters

| Name | Arguments | Return Type | Description |
|-|---|
|set_payload | bytes | None | Sets the message's payload. May raise an exception if argument signature mismatches |
|set_channel | str | None | Sets the message's tuning channel. May raise an exception if argument signature mismatches, or is invalid (len > 255) |
|set_timestamp| int | None | Sets the message's emission timestamp. May raise an exception if argument signature mismatches, or is invalid (timestamp < 0) |
|set_ttl| int | None | Sets the message's Time To Live. May raise an exception if argument signature mismatches, or is invalid (60s < ttl < 62h) |

#### The constructor and its KWargs

The construction of a message doesn't require one to call every single setter every time. The constructor uses the following keyword argument names to automatically set the provided data upon construction, using default values as follows :

| Keyword Argument | Type | Default |
|-|--|
| channel | str | "" |
| ttl | int | 60 |
| payload | bytes | None |

### Conversion methods

 - Implosion : when needed, a message object may be collapsed from a manipulable data structure, as described in this documentation, into a binary data blob. This implosion process is designed to assist with the composition of binary packets sent over the network.
 The implosion process will verify (albeit unnecessarily) every single field's type and validity, then proceed to write binary equivalents of those values (usig, channel, timestamp, ttl, etc...) into a binary sequence that is then compressed and returned. If, by accident, the imploded data is above our maximum packet data, an error is raised.
 - Explosion : A class method of "Message" is used to decompress and parse a binary blob into an usable message object. It basically performs the inverse operation of "implode".

### Control Method

 - `is_alive` : a function to quickly check whether a message is still alive, which is to say whether the current timestamp is greater than the message's emission timestamp plus its time to live. Returns a boolean.
 - `is_complete` : Checks whether all the fields are provided for a message to be imploded. Returns a boolean.

### Implemented feature :

 - Equality assertion : you can check whether a message object is representing the same message as another object message using the "==" operator.
 - Non-equality assertion : you can check whether two message objects represent to different messages using the "!=" operator.
 - String representation : you can turn a message into a string representation of itself, and print it out.
 - Message initialization : discussed earlier. Capable of using provided data for field initialization.
