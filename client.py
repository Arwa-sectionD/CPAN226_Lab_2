# This program was modified by Arwa Abdirahman / N01709742

import socket
import argparse
import time
import os
import struct  # IMPROVEMENT: Add struct to pack/unpack sequence numbers (4 bytes)

def run_client(target_ip, target_port, input_file):
    # 1. Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.25)  # IMPROVEMENT: Add timeout so we can resend if ACK is lost
    server_address = (target_ip, target_port)

    print(f"[*] Sending file '{input_file}' to {target_ip}:{target_port}")

    if not os.path.exists(input_file):
        print(f"[!] Error: File '{input_file}' not found.")
        return

    seq_num = 0  # IMPROVEMENT: Sequence number starts at 0 and increases per chunk

    try:
        with open(input_file, 'rb') as f:
            while True:
                # Read a chunk of the file
                chunk = f.read(1024) # IMPROVEMENT: Smaller chunks to avoid UDP message too large error


                if not chunk:
                    # End of file reached
                    break

                header = struct.pack("!I", seq_num)  # IMPROVEMENT: Pack seq_num into 4 bytes (network order)
                packet = header + chunk  # IMPROVEMENT: New packet format = [seq_num(4 bytes) | data]

                while True:  # IMPROVEMENT: Stop-and-wait loop (send until correct ACK received)
                    sock.sendto(packet, server_address)  # IMPROVEMENT: Send the packet with header + data

                    try:  # IMPROVEMENT: Try to receive an ACK
                        ack_bytes, _ = sock.recvfrom(1024)  # IMPROVEMENT: Receive ACK from server
                        if len(ack_bytes) >= 4:  # IMPROVEMENT: ACK should contain at least 4 bytes
                            ack_num = struct.unpack("!I", ack_bytes[:4])[0]  # IMPROVEMENT: Read ACK sequence number
                            if ack_num == seq_num:  # IMPROVEMENT: If ACK matches the packet we sent
                                break  # IMPROVEMENT: Good! move on to next chunk
                    except socket.timeout:  # IMPROVEMENT: If no ACK arrives, resend the same packet
                        continue  # IMPROVEMENT: Go back to sendto() again

                seq_num += 1  # IMPROVEMENT: Increase sequence number for next chunk

                # Optional: Small sleep to prevent overwhelming the OS buffer locally
                # (In a perfect world, we wouldn't need this, but raw UDP is fast!)
                time.sleep(0.001)

        # Send empty packet to signal "End of File" (reliable with ACK)
        end_header = struct.pack("!I", seq_num)  # IMPROVEMENT: END packet uses the next sequence number
        end_packet = end_header + b''  # IMPROVEMENT: END packet = header + empty payload

        while True:  # IMPROVEMENT: Keep sending END until server ACKs it (handles packet loss)
            sock.sendto(end_packet, server_address)  # IMPROVEMENT: Send END packet to server/relay

            try:  # IMPROVEMENT: Wait for ACK for the END packet
                ack_bytes, _ = sock.recvfrom(1024)  # IMPROVEMENT: Receive ACK from server
                if len(ack_bytes) >= 4:  # IMPROVEMENT: ACK must include 4 bytes for sequence number
                    ack_num = struct.unpack("!I", ack_bytes[:4])[0]  # IMPROVEMENT: Extract ACK sequence number
                    if ack_num == seq_num:  # IMPROVEMENT: If ACK matches END seq_num, we are done
                        break  # IMPROVEMENT: Stop resending END
            except socket.timeout:  # IMPROVEMENT: If END or its ACK is lost, try again
                continue  # IMPROVEMENT: Loop again and resend END

        print("[*] File transmission complete.")  # IMPROVEMENT: Only print success after END is ACKed

    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Naive UDP File Sender")
    parser.add_argument("--target_ip", type=str, default="127.0.0.1", help="Destination IP (Relay or Server)")
    parser.add_argument("--target_port", type=int, default=12000, help="Destination Port")
    parser.add_argument("--file", type=str, required=True, help="Path to file to send")
    args = parser.parse_args()

    run_client(args.target_ip, args.target_port, args.file)  # IMPROVEMENT: Call run_client with correct arguments
