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
