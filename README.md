
# DRTP
In this portfolio we have implemented a file transfer protocol called DRTP. The application have the functionality to transfer any type of data from one end to other end. Te user should specify what type of file they are going to transfer both in the client and server side. 
# usage
The server can be run by writing the following in the command line. 
#
    python3 application.py -s -i 10.x.x.x -p xxxx -f xxxx.jpg -r reliable method
On the other hand the client side can be run by writing the following in the command line. 
#
    python3 application.py -c -i 10.x.x.x -p xxxx -f xxxx.jpg -r reliable method -T format
# Test cases
# Stop-and-wait
	python3 application.py -s -i 10.x.x.x -p xxxx -f xxxx.jpg -r stop-and-wait -T -seqnr-
	python3 application.py -c -i 10.x.x.x -p xxxx -f xxxx.jpg -r stop-and-wait -T format
# Go-back-N
	python3 application.py -s -i 10.x.x.x -p xxxx -f xxxx.jpg -r gbn -T -seqnr-
	python3 application.py -c -i 10.x.x.x -p xxxx -f xxxx.jpg -r gbn -T format
# Selective-Repeat
	python3 application.py -s -i 10.x.x.x -p xxxx -f xxxx.jpg -r sr -T -seqnr-
	python3 application.py -c -i 10.x.x.x -p xxxx -f xxxx.jpg -r sr -T format
