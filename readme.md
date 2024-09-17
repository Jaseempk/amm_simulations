# Uniswap V3 AMM Simulation Script

## Overview

This Python script simulates the behavior of an Automated Market Maker (AMM) on Uniswap V3. The primary objective of the script is to model and analyze liquidity pool performance and fee adjustments based on historical swap data. It incorporates a dynamic fee mechanism to balance fees in response to price movements, optimizing for liquidity provider returns and mitigating inefficiencies.

## Features

- Fetches Uniswap V3 pool data and historical swap data from The Graph API.
- Simulates AMM behavior with dynamic fee adjustments based on price movement.
- Calculates liquidity provider returns and price efficiency.
- Finds the optimal fee adjustment parameter (`c`) to balance buy and sell fees and prevent negative fees.

## Requirements

- Python 3.x
- `requests` for API interactions
- `pandas` for timestamp calculations
- `numpy` for numerical operations
- `web3` for Ethereum interaction
- `decimal` for high precision arithmetic

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/Jaseempk/amm_simulations.git
   cd amm_simulations
   ```

2. **Install the required packages:**

   ```bash
   pip install requests pandas numpy web3
   ```

## Configuration

Modify the script to include your specific pool ID, fee tiers, and liquidity positions as needed. The script is currently configured for the ETH/USDC 0.3% pool on Ethereum Mainnet.

## Usage

1. **Update the Pool ID and other parameters in the `main()` function as required.**

2. **Run the script:**

   ```bash
   python amm_simulations.py
   ```

   The script will:

   - Fetch pool and swap data.
   - Simulate AMM behavior with different fee adjustment values (`c`).
   - Print results for negative fees, liquidity provider returns, and price efficiency.
   - Identify the optimal value of `c` based on the results.
