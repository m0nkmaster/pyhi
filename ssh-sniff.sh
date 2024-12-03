#!/bin/bash

# List of IP addresses to check
ips=(
    "192.168.0.40"
    "192.168.0.209"
    "192.168.0.56"
    "192.168.0.131"
    "192.168.0.57"
    "192.168.0.140"
    "192.168.0.28"
    "192.168.0.107"
    "192.168.0.101"
    "192.168.0.20"
    "192.168.0.250"
    "192.168.0.93"
    "192.168.0.163"
    "192.168.0.33"
    "192.168.0.39"
    "192.168.0.67"
    "192.168.0.21"
    "192.168.0.208"
    "192.168.0.145"
    "192.168.0.141"
    "192.168.0.96"
    "192.168.0.41"  # iPhone
    "192.168.0.43"  # AutoPack_Sweeper
    "192.168.0.180" # ESP_632532
)

# Port to check (SSH default port)
port=22

# Create a temporary directory for results
tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT

echo "Starting parallel SSH port checks..."

# Start all checks in parallel
for ip in "${ips[@]}"; do
    {
        if nc -zv -w1 $ip $port 2>&1 | grep -q "succeeded"; then
            echo "$ip" > "$tmp_dir/$ip.success"
        fi
    } &
done

# Monitor progress
total=${#ips[@]}
start_time=$SECONDS

# Show progress
while true; do
    running=$(jobs -p | wc -l | tr -d ' ')
    completed=$((total - running))
    printf "\rProgress: [%d/%d]   " $completed $total
    
    # Check if we've been running too long (15 seconds max)
    if [ $((SECONDS - start_time)) -gt 15 ]; then
        echo -e "\nTimeout after 15 seconds!"
        kill $(jobs -p) 2>/dev/null
        break
    fi
    
    # Check if all jobs are done
    [ "$running" -eq 0 ] && break
    
    sleep 0.1
done

echo -e "\n\nResults:"
found_open=false
for ip in "${ips[@]}"; do
    if [ -f "$tmp_dir/$ip.success" ]; then
        echo "✅ Port $port is open on $ip"
        found_open=true
    fi
done

if [ "$found_open" = false ]; then
    echo "No open SSH ports found."
fi

# Report completion status
if [ $completed -lt $total ]; then
    echo -e "\nNote: Only $completed out of $total checks completed."
else
    echo -e "\nAll $total checks completed."
fi