#!/usr/bin/expect

set outfile "/client/cifs_write.txt"
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

spawn smbclient -q -U% \\\\$mhost -c 'put /client/ecfirst.txt'

expect {
	timeout {puts $ofileid "\tFailed to connect"; wait; continue}
	eof { puts $ofileid "\tFailed to put"; wait; continue}
	"putting file ecfirst.txt *"
}

send_user "\n!!! Uploaded to $mhost"
puts $ofileid "\tUploaded"

spawn smbclient -q -U% \\\\$mhost -c 'rm /client/ecfirst.txt'

}
close $ofileid
close $ifileid
