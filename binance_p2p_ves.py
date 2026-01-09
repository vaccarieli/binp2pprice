#!/usr/bin/env python3
"""
Binance P2P VES Price Checker
Fetches current buy/sell offers for VES on Binance P2P
"""

import requests
import json
import argparse

def get_p2p_offers(trade_type, asset="USDT", fiat="VES", payment_methods=None):
    """
    Fetch P2P offers from Binance
    
    Args:
        trade_type: "BUY" or "SELL" 
        asset: Crypto asset (default: USDT)
        fiat: Fiat currency (default: VES)
        payment_methods: List of payment methods (optional)
    """
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    
    payload = {
        "page": 1,
        "rows": 10,
        "payTypes": payment_methods or [],
        "asset": asset,
        "tradeType": trade_type,
        "fiat": fiat,
        "publisherType": None
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def filter_offers_by_exclude(offers, exclude_methods):
    """Filter out offers that have any excluded payment methods"""
    if not exclude_methods:
        return offers
    
    # Normalize exclude methods for comparison
    exclude_normalized = [m.strip().lower() for m in exclude_methods]
    
    filtered = []
    for offer in offers:
        trade_methods = offer.get("adv", {}).get("tradeMethods", [])
        methods = [m.get("tradeMethodName", "") for m in trade_methods if m.get("tradeMethodName")]
        methods_normalized = [m.strip().lower() for m in methods]
        
        # Skip offer if ANY of its methods are in the exclude list
        has_excluded = any(method in exclude_normalized for method in methods_normalized)
        if not has_excluded:
            filtered.append(offer)
    
    return filtered

def display_offers(data, trade_type, exclude_methods=None):
    """Display P2P offers in a readable format"""
    if not data or "data" not in data:
        print(f"No data available for {trade_type} offers")
        return
    
    offers = data.get("data", [])
    
    if not offers:
        print(f"No {trade_type} offers found")
        return
    
    # Filter out offers with excluded payment methods
    if exclude_methods:
        filtered_offers = []
        for offer in offers:
            trade_methods = offer.get("adv", {}).get("tradeMethods", [])
            methods = [m.get("tradeMethodName", "") for m in trade_methods if m.get("tradeMethodName")]
            # Keep offer only if it doesn't exclusively use excluded methods
            if not all(method in exclude_methods for method in methods):
                filtered_offers.append(offer)
        offers = filtered_offers
    
    if not offers:
        print(f"No {trade_type} offers found after filtering")
        return
    
    print(f"\n{'='*70}")
    print(f"{trade_type} OFFERS (VES/USDT)")
    print(f"{'='*70}")
    
    for i, offer in enumerate(offers, 1):
        adv = offer.get("adv", {})
        advertiser = offer.get("advertiser", {})
        
        price = float(adv.get("price", 0))
        min_usdt = float(adv.get("minSingleTransAmount", 0))
        max_usdt = float(adv.get("dynamicMaxSingleTransAmount", 0))
        available = adv.get("surplusAmount", "N/A")
        
        # Calculate VES limits
        min_ves = min_usdt * price
        max_ves = max_usdt * price
        
        # Payment methods
        trade_methods = adv.get("tradeMethods", [])
        payment_methods = ", ".join([m.get("tradeMethodName", "") for m in trade_methods if m.get("tradeMethodName")])
        
        print(f"\n{i}. Price: {price:.2f} VES/USDT")
        print(f"   Available: {available} USDT")
        print(f"   Limits: {min_ves:,.2f} - {max_ves:,.2f} VES")
        print(f"   Payment: {payment_methods}")
        print(f"   Trader: {advertiser.get('nickName', 'N/A')} (Orders: {advertiser.get('monthOrderCount', 0)})")

def main():
    parser = argparse.ArgumentParser(description='Check Binance P2P VES prices')
    parser.add_argument('--payment-methods', '-p', nargs='+', 
                        help='Filter by payment methods (e.g., -p "Bank Transfer")')
    parser.add_argument('--exclude', '-e', nargs='+',
                        help='Exclude payment methods (e.g., -e "Recarga Pines")')
    args = parser.parse_args()
    
    payment_methods = args.payment_methods if args.payment_methods else []
    
    # Default exclude list - always exclude these payment methods
    default_excludes = ["Recarga Pines"]
    exclude_methods = default_excludes + (args.exclude if args.exclude else [])
    
    if payment_methods:
        print(f"Filtering for: {', '.join(payment_methods)}")
    if exclude_methods:
        print(f"Excluding: {', '.join(exclude_methods)}")
    
    print("Fetching Binance P2P VES prices...\n")
    
    # Fetch filtered offers for display
    buy_data = get_p2p_offers("BUY", payment_methods=payment_methods)
    display_offers(buy_data, "BUY", exclude_methods)
    
    sell_data = get_p2p_offers("SELL", payment_methods=payment_methods)
    display_offers(sell_data, "SELL", exclude_methods)
    
    # Fetch unfiltered offers for comparison
    buy_data_all = get_p2p_offers("BUY", payment_methods=[])
    sell_data_all = get_p2p_offers("SELL", payment_methods=[])
    
    # Summary
    if buy_data and sell_data:
        buy_offers = filter_offers_by_exclude(buy_data.get("data", []), exclude_methods)
        sell_offers = filter_offers_by_exclude(sell_data.get("data", []), exclude_methods)
        
        if buy_offers and sell_offers:
            best_buy_offer = buy_offers[0]
            best_sell_offer = sell_offers[0]
            
            best_buy = float(best_buy_offer.get("adv", {}).get("price", 0))
            best_sell = float(best_sell_offer.get("adv", {}).get("price", 0))
            
            buy_trader = best_buy_offer.get("advertiser", {}).get("nickName", "N/A")
            buy_orders = best_buy_offer.get("advertiser", {}).get("monthOrderCount", 0)
            
            sell_trader = best_sell_offer.get("advertiser", {}).get("nickName", "N/A")
            sell_orders = best_sell_offer.get("advertiser", {}).get("monthOrderCount", 0)
            
            print(f"\n{'='*70}")
            print("SUMMARY")
            print(f"{'='*70}")
            
            if payment_methods or exclude_methods:
                filter_desc = []
                if payment_methods:
                    filter_desc.append(f"with {', '.join(payment_methods)}")
                if exclude_methods:
                    filter_desc.append(f"excluding {', '.join(exclude_methods)}")
                print(f"With filters ({' '.join(filter_desc)}):")
            print(f"Best BUY price:  {best_buy:.2f} VES/USDT (you buy USDT)")
            print(f"  Seller: {buy_trader} (Orders: {buy_orders})")
            print(f"Best SELL price: {best_sell:.2f} VES/USDT (you sell USDT)")
            print(f"  Buyer: {sell_trader} (Orders: {sell_orders})")
            print(f"Spread: {best_buy - best_sell:.2f} VES ({((best_buy/best_sell - 1) * 100):.2f}%)")
            
            # Show best overall rates if filtering
            if (payment_methods or exclude_methods) and buy_data_all and sell_data_all:
                buy_offers_all = filter_offers_by_exclude(buy_data_all.get("data", []), exclude_methods)
                sell_offers_all = filter_offers_by_exclude(sell_data_all.get("data", []), exclude_methods)
                
                if buy_offers_all and sell_offers_all:
                    best_buy_all_offer = buy_offers_all[0]
                    best_sell_all_offer = sell_offers_all[0]
                    
                    best_buy_all = float(best_buy_all_offer.get("adv", {}).get("price", 0))
                    best_sell_all = float(best_sell_all_offer.get("adv", {}).get("price", 0))
                    
                    buy_trader_all = best_buy_all_offer.get("advertiser", {}).get("nickName", "N/A")
                    buy_orders_all = best_buy_all_offer.get("advertiser", {}).get("monthOrderCount", 0)
                    buy_methods_all = ", ".join([m.get("tradeMethodName", "") for m in best_buy_all_offer.get("adv", {}).get("tradeMethods", []) if m.get("tradeMethodName")])
                    
                    sell_trader_all = best_sell_all_offer.get("advertiser", {}).get("nickName", "N/A")
                    sell_orders_all = best_sell_all_offer.get("advertiser", {}).get("monthOrderCount", 0)
                    sell_methods_all = ", ".join([m.get("tradeMethodName", "") for m in best_sell_all_offer.get("adv", {}).get("tradeMethods", []) if m.get("tradeMethodName")])
                    
                    print(f"\nBest overall rates (any payment method):")
                    print(f"Best BUY price:  {best_buy_all:.2f} VES/USDT")
                    print(f"  Seller: {buy_trader_all} (Orders: {buy_orders_all}) - {buy_methods_all}")
                    print(f"Best SELL price: {best_sell_all:.2f} VES/USDT")
                    print(f"  Buyer: {sell_trader_all} (Orders: {sell_orders_all}) - {sell_methods_all}")
                    print(f"Spread: {best_buy_all - best_sell_all:.2f} VES ({((best_buy_all/best_sell_all - 1) * 100):.2f}%)")

if __name__ == "__main__":
    main()
