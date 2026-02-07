# This program was modified by Arwa Abdirahman / N01709742

import socket
import argparse
import struct  # IMPROVEMENT: Needed to unpack the 4-byte sequence number and pack ACKs

def run_server(port, output_file):
    # 1. Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # 2. Bind the socket to the port (0.0.0.0 means all interfaces)
    server_address = ('', port)
    print(f"[*] Server listening on port {port}")
    print(f"[*] Server will save each received file as 'received_<ip>_<port>.jpg' based on sender.")
    sock.bind(server_address)

    # 3. Keep listening for new transfers
    try:
        while True:
            f = None
            sender_filename = None
            reception_started = False

            expected_seq = 0  # IMPROVEMENT: Track the next sequence number we want to write
            buffer = {}       # IMPROVEMENT: Store out-of-order packets here: {seq_num: data}
            end_seq = None    # IMPROVEMENT: Remember which sequence number was the END packet

            while True:
                packet, addr = sock.recvfrom(65535)  # IMPROVEMENT: Receive up to max UDP packet size safely

                if len(packet) < 4:  # IMPROVEMENT: If packet is too small, ignore it safely
                    continue  # IMPROVEMENT: Skip invalid packets

                seq_num = struct.unpack("!I", packet[:4])[0]  # IMPROVEMENT: First 4 bytes = sequence number
                data = packet[4:]  # IMPROVEMENT: The rest is the file data (may be empty for END)

                ack = struct.pack("!I", seq_num)  # IMPROVEMENT: ACK contains the sequence number we received
                sock.sendto(ack, addr)  # IMPROVEMENT: Send ACK back (helps client resend if ACK is lost)

                if f is None:  # IMPROVEMENT: Open output file on first valid packet
                    print("==== Start of reception ====")
                    ip, sender_port = addr
                    sender_filename = f"received_{ip.replace('.', '_')}_{sender_port}.jpg"
                    f = open(sender_filename, 'wb')
                    print(f"[*] First packet received from {addr}. File opened for writing as '{sender_filename}'.")

                if seq_num == expected_seq:  # IMPROVEMENT: This is the exact packet we need next
                    if not data:  # IMPROVEMENT: Empty data means END packet
                        end_seq = seq_num  # IMPROVEMENT: Save END sequence number
                        print(f"[*] End packet received (seq {end_seq}). Waiting for missing packets if any...")  # IMPROVEMENT: Explain behavior
                        expected_seq += 1  # IMPROVEMENT: Move expected forward past END
                    else:
                        f.write(data)  # IMPROVEMENT: Write in-order data to disk
                        expected_seq += 1  # IMPROVEMENT: Move to next expected sequence number

                    # IMPROVEMENT: After writing, flush any buffered packets that now become in-order
                    while expected_seq in buffer:  # IMPROVEMENT: Keep writing buffered packets in correct order
                        buffered_data = buffer.pop(expected_seq)  # IMPROVEMENT: Remove packet from buffer
                        if not buffered_data:  # IMPROVEMENT: Buffered empty data means END packet
                            end_seq = expected_seq  # IMPROVEMENT: Record END seq if it arrived out-of-order
                            print(f"[*] End packet received from buffer (seq {end_seq}).")  # IMPROVEMENT: Inform END from buffer
                            expected_seq += 1  # IMPROVEMENT: Move past END
                            continue  # IMPROVEMENT: Keep flushing remaining buffered packets (if any)
                        f.write(buffered_data)  # IMPROVEMENT: Write buffered data in-order
                        expected_seq += 1  # IMPROVEMENT: Increase expected sequence number

                    # IMPROVEMENT: Stop only when END has been received and all packets up to END are written
                    if end_seq is not None and expected_seq > end_seq:  # IMPROVEMENT: Finished writing all packets including END
                        print("[*] All packets received. Closing file.")  # IMPROVEMENT: Completion message
                        break  # IMPROVEMENT: Exit inner receive loop

                elif seq_num > expected_seq:  # IMPROVEMENT: Packet arrived early (out-of-order)
                    if seq_num not in buffer:  # IMPROVEMENT: Only store if we don’t already have it
                        buffer[seq_num] = data  # IMPROVEMENT: Save for later when we reach this seq

                else:
                    # IMPROVEMENT: Duplicate/old packet. Ignore it safely.
                    pass  # IMPROVEMENT: Do nothing for old packets

            if f:
                f.close()
            print("==== End of reception ====")

    except KeyboardInterrupt:
        print("\n[!] Server stopped manually.")
    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        sock.close()
        print("[*] Server socket closed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Naive UDP File Receiver")
    parser.add_argument("--port", type=int, default=12001, help="Port to listen on")
    parser.add_argument("--output", type=str, default="received_file.jpg", help="File path to save data")
    args = parser.parse_args()

    try:
        run_server(args.port, args.output)
    except KeyboardInterrupt:
        print("\n[!] Server stopped manually.")
    except Exception as e:
        print(f"[!] Error: {e}")
