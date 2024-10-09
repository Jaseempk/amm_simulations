import requests
import pandas as pd
import numpy as np
from decimal import Decimal
from web3 import Web3

# Constants
SUBGRAPH_URL = "https://gateway.thegraph.com/api/<>/subgraphs/id/5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV"
MIN_TICK = -887272
MAX_TICK = 887272
Q96 = 2**96

def fetch_pool_data(pool_id):
    query = """
    query ($poolId: ID!) {
        pool(id: $poolId) {
            tick
            sqrtPrice
            liquidity
            feeTier
            token0 {
                decimals
            }
            token1 {
                decimals
            }
        }
    }
    """
    response = requests.post(SUBGRAPH_URL, json={"query": query, "variables": {"poolId": pool_id}})
    return response.json()["data"]["pool"]

def fetch_historical_data(pool_id, start_timestamp, end_timestamp):
    query = """
    query ($poolId: String!, $startTime: Int!, $endTime: Int!) {
        swaps(
            where: {pool: $poolId, timestamp_gte: $startTime, timestamp_lte: $endTime}
            orderBy: timestamp
            orderDirection: asc
            first: 1000
        ) {
            timestamp
            amount0
            amount1
            sqrtPriceX96
            tick
            logIndex
        }
    }
    """
    variables = {
        "poolId": pool_id,
        "startTime": start_timestamp,
        "endTime": end_timestamp
    }
    response = requests.post(SUBGRAPH_URL, json={"query": query, "variables": variables})
    return response.json()["data"]["swaps"]

def tick_to_price(tick):
    return 1.0001**tick

def price_to_tick(price):
    return int(np.log(price) / np.log(1.0001))

def tick_to_sqrt_price(tick):
    return Decimal(1.0001 ** (tick / 2))

def sqrt_price_to_tick(sqrt_price):
    return int(np.log(float(sqrt_price**2)) / np.log(1.0001))

def calculate_amount0(sqrt_price_a, sqrt_price_b, liquidity):
    return int(liquidity * (sqrt_price_b - sqrt_price_a) / (sqrt_price_a * sqrt_price_b))

def calculate_amount1(sqrt_price_a, sqrt_price_b, liquidity):
    return int(liquidity * (sqrt_price_b - sqrt_price_a))

class LiquidityPosition:
    def __init__(self, lower_tick, upper_tick, liquidity):
        self.lower_tick = lower_tick
        self.upper_tick = upper_tick
        self.liquidity = liquidity

class UniswapV3Pool:
    def __init__(self, sqrt_price, tick, liquidity, fee_tier, token0_decimals, token1_decimals):
        self.sqrt_price = Decimal(sqrt_price)
        self.tick = int(tick)
        self.liquidity = Decimal(liquidity)
        self.fee_tier = int(fee_tier)
        self.token0_decimals = int(token0_decimals)
        self.token1_decimals = int(token1_decimals)
        self.positions = []

    def add_position(self, lower_tick, upper_tick, liquidity):
        self.positions.append(LiquidityPosition(lower_tick, upper_tick, liquidity))

    def update_liquidity(self, new_tick):
        active_liquidity = Decimal(0)
        for position in self.positions:
            if position.lower_tick <= new_tick < position.upper_tick:
                active_liquidity += position.liquidity
        self.liquidity = active_liquidity

    def swap(self, amount_in, zero_for_one, fee_adjustment):
        sqrt_price_limit = tick_to_sqrt_price(MIN_TICK if zero_for_one else MAX_TICK)

        amount_remaining = amount_in
        while amount_remaining > Decimal('0'):
            next_tick = self.get_next_initialized_tick(zero_for_one)
            sqrt_price_next = tick_to_sqrt_price(next_tick)

            sqrt_price_target = min(sqrt_price_next, sqrt_price_limit) if zero_for_one else max(sqrt_price_next, sqrt_price_limit)

            amount_in_step, amount_out_step = self.compute_swap_step(sqrt_price_target, amount_remaining, zero_for_one)

            if amount_in_step == Decimal('0'):
                break
            
            amount_remaining -= amount_in_step

            # Apply fee
            fee = amount_in_step * (Decimal(self.fee_tier) / Decimal('1e6') + fee_adjustment)
            amount_in_step -= fee

            # Update pool state
            self.sqrt_price = sqrt_price_target
            self.tick = sqrt_price_to_tick(self.sqrt_price)
            self.update_liquidity(self.tick)

        return amount_in - amount_remaining

    def compute_swap_step(self, sqrt_price_target, amount_remaining, zero_for_one):
        if zero_for_one:
            amount0 = calculate_amount0(sqrt_price_target, self.sqrt_price, self.liquidity)
            amount1 = calculate_amount1(sqrt_price_target, self.sqrt_price, self.liquidity)
        else:
            amount0 = calculate_amount0(self.sqrt_price, sqrt_price_target, self.liquidity)
            amount1 = calculate_amount1(self.sqrt_price, sqrt_price_target, self.liquidity)
        
        return min(amount_remaining, amount0 if zero_for_one else amount1), amount1 if zero_for_one else amount0

    def get_next_initialized_tick(self, zero_for_one):
        current_tick = self.tick
        while True:
            current_tick += -1 if zero_for_one else 1
            for position in self.positions:
                if position.lower_tick == current_tick or position.upper_tick == current_tick:
                    return current_tick
            if current_tick <= MIN_TICK or current_tick >= MAX_TICK:
                return MIN_TICK if zero_for_one else MAX_TICK

def simulate_amm(pool, swaps, base_fee, c_value, price_threshold=Decimal('0.02')):
    negative_fee_count = 0
    total_lp_returns = Decimal('0')
    price_efficiency = Decimal('0')

    # Convert c_value to Decimal
    c_value = Decimal(str(c_value))

    for swap in swaps:
        amount0 = Decimal(swap['amount0'])
        amount1 = Decimal(swap['amount1'])
        
        zero_for_one = amount0 > 0
        amount_in = abs(amount0 if zero_for_one else amount1)
        
        # Calculate price impact
        old_price = float(pool.sqrt_price ** 2)  # Ensure float for division
        new_sqrt_price = float(Decimal(swap['sqrtPriceX96']) / Decimal(str(Q96)))
        delta = (new_sqrt_price ** 2 - old_price) / old_price
        
        # Dynamic fee adjustment based on price delta threshold
        if (zero_for_one and delta > price_threshold) or (not zero_for_one and delta < -price_threshold):
            c_delta = c_value * abs(Decimal(delta))
            
            # Increase the fee in the direction of price movement
            if zero_for_one:  # Price of ETH increasing (high buy pressure)
                fee_adjustment = c_delta
                buy_fee = base_fee + fee_adjustment
                # sell_fee = max(base_fee - fee_adjustment, Decimal('0'))  # Prevent negative sell fee
                if((base_fee-fee_adjustment)<0):
                    sell_fee=base_fee
                else:
                    sell_fee=base_fee-fee_adjustment
            else:  # Price of ETH decreasing (high sell pressure)
                fee_adjustment = c_delta
                sell_fee = base_fee + fee_adjustment
                # buy_fee = max(base_fee - fee_adjustment, Decimal('0'))  # Prevent negative buy fee
                if((base_fee-fee_adjustment)<0):
                    buy_fee=base_fee
                else:
                    buy_fee=base_fee-fee_adjustment
        else:
            # Default fee if no significant price shift
            buy_fee = sell_fee = base_fee

        # Apply the relevant fee depending on trade direction
        fee_adjustment = buy_fee if zero_for_one else sell_fee

        if base_fee + fee_adjustment < 0:
            negative_fee_count += 1
            fee_adjustment = -Decimal(str(base_fee))  # Ensure fee doesn't go negative
        
        # Perform swap
        amount_in_actual = pool.swap(amount_in, zero_for_one, fee_adjustment)
        
        # Calculate LP returns
        total_lp_returns += amount_in_actual * (Decimal(str(base_fee)) + fee_adjustment)
        
        price_efficiency += abs(Decimal(delta))

    avg_price_efficiency = price_efficiency / Decimal(str(len(swaps)))
    return negative_fee_count, total_lp_returns, avg_price_efficiency


def main():
    # ETH/USDC 0.3% pool on mainnet
    pool_id = "0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8"
    
    print("Fetching pool data...")
    pool_data = fetch_pool_data(pool_id)
    
    pool = UniswapV3Pool(
        sqrt_price=int(pool_data['sqrtPrice']) / Q96,
        tick=int(pool_data['tick']),
        liquidity=pool_data['liquidity'],
        fee_tier=int(pool_data['feeTier']),
        token0_decimals=int(pool_data['token0']['decimals']),
        token1_decimals=int(pool_data['token1']['decimals'])
    )
    
    # Add some mock liquidity positions
    pool.add_position(price_to_tick(1500), price_to_tick(2500), Decimal('1000000000000000000'))
    pool.add_position(price_to_tick(1800), price_to_tick(2200), Decimal('2000000000000000000'))
    
    # Fetch historical data for the last 24 hours
    end_time = int(pd.Timestamp.now().timestamp())
    start_time = end_time - (24 * 60 * 60)
    
    print("Fetching historical swap data...")
    swaps = fetch_historical_data(pool_id, start_time, end_time)
    print(f"Fetched {len(swaps)} swaps")

    base_fee = Decimal(str(pool.fee_tier)) / Decimal('1000000')
    c_values = [Decimal(str(c)) for c in np.linspace(0.1, 2.0, 20)]
    results = []

    print("Running simulations...")
    for c in c_values:
        neg_count, lp_returns, price_efficiency = simulate_amm(pool, swaps, base_fee, c)
        results.append((c, neg_count, lp_returns, price_efficiency))
        print(f"c={c:.2f}: Negative fees: {neg_count}, LP returns: {lp_returns:.2f}, Price efficiency: {price_efficiency:.6f}")

    # Find optimal c value
    valid_results = [(c, returns, efficiency) for c, neg, returns, efficiency in results if neg == 0]
    if valid_results:
        optimal_c = max(valid_results, key=lambda x: x[1])[0]
        print(f"\nOptimal c value: {optimal_c:.4f}")
    else:
        print("\nNo valid c value found that prevents negative fees. Consider increasing the base fee or adjusting the c value range.")

if __name__ == "__main__":
    main()