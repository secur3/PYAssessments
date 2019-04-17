#!/usr/bin/expect

set outfile "/client/cifs_read.txt"
set ofileid [open $outfile "w"]
set infile "/client/Book1.csv"
set ifileid [open "$infile" r]
set data [read $ifileid]
log_user 0

foreach line  $data {
set tmp [regsub "," $line "\\\\\\\\"]
set mhost [regsub " " $tmp "\\\\ "]
send_user "\n$mhost"
puts $ofileid "$mhost"

spawn smbclient -q -U% \\\\$mhost

expect {
	timeout {puts $ofileid "\tFailed to connect"; continue}
	eof { puts $ofileid "\tFailed to connect"; continue}
	"smb: *"
}

send_user "\n!!! Connected to $mhost"
puts $ofileid "\tConnected"
}
close $ofileid
close $ifileid
