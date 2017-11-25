#!/usr/bin/ruby
require 'socket'

hostname = "127.0.0.1"
begin
	port = File::open("/tmp/unisocket_port").read().to_i
rescue Errno::ENOENT
	puts "Could not open port file. Is the service running?"
	exit
end

death_sequence = "\x57\x68\x61\x74\x20\x69\x73\x20\x6c\x6f\x76\x65\x3f\x20\x42\x61\x62\x79\x20\x64\x6f\x6e\x27\x74\x20\x68\x75\x72\x74\x20\x6d\x65\x2c\x20\x64\x6f\x6e\x27\x74\x20\x68\x75\x72\x74\x20\x6d\x65\x2c\x20\x6e\x6f\x20\x6d\x6f\x72\x65"

puts "Attacking on port #{port}"

s = TCPSocket.open(hostname, port)
s.print("\x01\0")
s.print("\x05\x00\x03moo")
s.print("\x05\0\0")
puts s.recv(1024)
s.print("\xffmoostardinette") # Malformed data
puts s.recv(1024)
s.print(death_sequence)
puts s.recv(1024)
s.close
