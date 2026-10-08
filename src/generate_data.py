"""
Canadian Tire Corporation (CTC) - Synthetic Retail Data Generator
Generates realistic POS transactions, stores, products, and ORC fraud scenarios.
"""

import os
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from faker import Faker

# Seed for reproducibility
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
fake = Faker("en_CA")

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw"
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

START_DATE = datetime(2026, 8, 1, 8, 0, 0)
SIMULATION_DAYS = 30


def generate_stores() -> pd.DataFrame:
    """Generates fictional Canadian Tire store locations across the GTA."""
    stores_data = [
        {"store_id": "STORE_101", "name": "Toronto - Eaton Centre", "city": "Toronto", "region": "GTA_CENTRAL"},
        {"store_id": "STORE_102", "name": "Toronto - Leslieville", "city": "Toronto", "region": "GTA_EAST"},
        {"store_id": "STORE_103", "name": "Etobicoke - Queensway", "city": "Etobicoke", "region": "GTA_WEST"},
        {"store_id": "STORE_104", "name": "Mississauga - Heartland", "city": "Mississauga", "region": "GTA_WEST"},
        {"store_id": "STORE_105", "name": "Mississauga - Meadowvale", "city": "Mississauga", "region": "GTA_WEST"},
        {"store_id": "STORE_106", "name": "Brampton - North", "city": "Brampton", "region": "GTA_WEST"},
        {"store_id": "STORE_107", "name": "Vaughan - Weston Rd", "city": "Vaughan", "region": "GTA_NORTH"},
        {"store_id": "STORE_108", "name": "Richmond Hill - Yonge", "city": "Richmond Hill", "region": "GTA_NORTH"},
        {"store_id": "STORE_109", "name": "Markham - East", "city": "Markham", "region": "GTA_NORTH"},
        {"store_id": "STORE_110", "name": "Scarborough - Cedarbrae", "city": "Scarborough", "region": "GTA_EAST"},
    ]
    df = pd.DataFrame(stores_data)
    df.to_csv(RAW_DATA_DIR / "stores.csv", index=False)
    return df


def generate_products() -> pd.DataFrame:
    """Generates CTC catalog SKUs categorized by theft risk."""
    products_data = [
        # High Risk: Power tools and automotive electronics (Primary ORC targets)
        {"sku": "SKU_TOOL_01", "name": "Mastercraft 20V Max Brushless Drill Kit", "category": "Hardware", "price": 179.99, "theft_tier": "HIGH"},
        {"sku": "SKU_TOOL_02", "name": "DeWalt 20V Max Cordless Impact Driver", "category": "Hardware", "price": 219.99, "theft_tier": "HIGH"},
        {"sku": "SKU_TOOL_03", "name": "Mastercraft 300-Piece Socket & Tool Set", "category": "Hardware", "price": 299.99, "theft_tier": "HIGH"},
        {"sku": "SKU_AUTO_01", "name": "MotoMaster Eliminator 1400A Booster Pack", "category": "Automotive", "price": 199.99, "theft_tier": "HIGH"},
        {"sku": "SKU_AUTO_02", "name": "NOCO Genius 10A Battery Charger", "category": "Automotive", "price": 149.99, "theft_tier": "HIGH"},
        
        # Medium Risk: Seasonal and camping
        {"sku": "SKU_SEAS_01", "name": "Yardworks 20V Cordless Grass Trimmer", "category": "Seasonal", "price": 119.99, "theft_tier": "MEDIUM"},
        {"sku": "SKU_CAMP_01", "name": "Woods 4-Person Dome Camping Tent", "category": "Outdoor", "price": 159.99, "theft_tier": "MEDIUM"},
        
        # Low Risk: Everyday consumables and liquids
        {"sku": "SKU_CONS_01", "name": "MotoMaster 5W-30 Synthetic Engine Oil 5L", "category": "Automotive", "price": 34.99, "theft_tier": "LOW"},
        {"sku": "SKU_CONS_02", "name": "Certified -40C Windshield Washer Fluid 3.78L", "category": "Automotive", "price": 4.99, "theft_tier": "LOW"},
        {"sku": "SKU_CONS_03", "name": "Simoniz Microfibre Wash Mitt", "category": "Automotive", "price": 9.99, "theft_tier": "LOW"},
        {"sku": "SKU_CONS_04", "name": "Mastercraft Precision Screwdriver Set 6-pc", "category": "Hardware", "price": 14.99, "theft_tier": "LOW"},
        {"sku": "SKU_CONS_05", "name": "Frank Sparkling Spring Water 12-Pack", "category": "Kitchen", "price": 5.99, "theft_tier": "LOW"},
    ]
    df = pd.DataFrame(products_data)
    df.to_csv(RAW_DATA_DIR / "products.csv", index=False)
    return df


def generate_transactions(stores_df: pd.DataFrame, products_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generates POS transactions simulating:
    1. Normal Shoppers
    2. Contractors (Hard Negatives / False Positives)
    3. ORC Return Rings (Coordinated Fraud)
    """
    transactions: List[Dict] = []
    labels: List[Dict] = []
    
    store_ids = stores_df["store_id"].tolist()
    high_risk_skus = products_df[products_df["theft_tier"] == "HIGH"]["sku"].tolist()
    low_risk_skus = products_df[products_df["theft_tier"] == "LOW"]["sku"].tolist()
    all_skus = products_df["sku"].tolist()
    sku_price_map = dict(zip(products_df["sku"], products_df["price"]))

    # ---------------------------------------------------------
    # 1. NORMAL SHOPPERS (1,500 customers, typical purchase/return patterns)
    # ---------------------------------------------------------
    for i in range(1500):
        # 60% swipe Triangle Rewards; 40% are anonymous/unlinked
        has_loyalty = random.random() < 0.60
        triangle_id = f"TRI_{fake.bothify(text='??#####').upper()}" if has_loyalty else None
        payment_token = f"TOK_CARD_{uuid.uuid4().hex[:12].upper()}"
        primary_store = random.choice(store_ids)
        
        # 1 to 4 shopping trips over the 30-day window
        num_trips = random.choices([1, 2, 3, 4], weights=[0.55, 0.25, 0.15, 0.05])[0]
        for _ in range(num_trips):
            trip_time = START_DATE + timedelta(
                days=random.randint(0, SIMULATION_DAYS - 2),
                hours=random.randint(9, 20),
                minutes=random.randint(0, 59)
            )
            tx_id = f"TX_PUR_{uuid.uuid4().hex[:10].upper()}"
            selected_sku = random.choice(all_skus)
            qty = random.randint(1, 2)
            amt = round(sku_price_map[selected_sku] * qty, 2)
            
            transactions.append({
                "transaction_id": tx_id,
                "timestamp": trip_time.strftime("%Y-%m-%d %H:%M:%S"),
                "store_id": primary_store,
                "transaction_type": "PURCHASE",
                "triangle_id": triangle_id,
                "payment_token": payment_token,
                "sku": selected_sku,
                "quantity": qty,
                "amount": amt,
                "is_receipted": True
            })
            labels.append({"transaction_id": tx_id, "is_fraud": 0, "scenario": "NORMAL"})

            # 5% probability of a legitimate return within 48-72 hours
            if random.random() < 0.05:
                ret_time = trip_time + timedelta(days=random.randint(1, 3), hours=random.randint(1, 4))
                ret_id = f"TX_RET_{uuid.uuid4().hex[:10].upper()}"
                transactions.append({
                    "transaction_id": ret_id,
                    "timestamp": ret_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "store_id": primary_store,
                    "transaction_type": "RETURN",
                    "triangle_id": triangle_id,
                    "payment_token": payment_token,
                    "sku": selected_sku,
                    "quantity": qty,
                    "amount": amt,
                    "is_receipted": True
                })
                labels.append({"transaction_id": ret_id, "is_fraud": 0, "scenario": "NORMAL"})

    # ---------------------------------------------------------
    # 2. COMMERCIAL CONTRACTORS (Hard Negatives / False Positives)
    # High volume, large purchases and returns, but legitimate.
    # ---------------------------------------------------------
    for c in range(15):
        contractor_triangle_id = f"TRI_PRO_{1000 + c}"
        contractor_card = f"TOK_CORP_{uuid.uuid4().hex[:12].upper()}"
        base_store = random.choice(store_ids)
        
        for day_offset in range(1, SIMULATION_DAYS - 1, 4):
            tx_time = START_DATE + timedelta(days=day_offset, hours=7, minutes=30)
            tx_id = f"TX_CON_{uuid.uuid4().hex[:10].upper()}"
            # Buying bulk hardware/tools
            selected_sku = random.choice(high_risk_skus)
            qty = random.randint(4, 8)
            amt = round(sku_price_map[selected_sku] * qty, 2)
            
            transactions.append({
                "transaction_id": tx_id,
                "timestamp": tx_time.strftime("%Y-%m-%d %H:%M:%S"),
                "store_id": base_store,
                "transaction_type": "PURCHASE",
                "triangle_id": contractor_triangle_id,
                "payment_token": contractor_card,
                "sku": selected_sku,
                "quantity": qty,
                "amount": amt,
                "is_receipted": True
            })
            labels.append({"transaction_id": tx_id, "is_fraud": 0, "scenario": "CONTRACTOR"})
            
            # Contractors return unused excess stock (high dollar value, but with receipt)
            ret_time = tx_time + timedelta(days=2, hours=9)
            ret_id = f"TX_CON_RET_{uuid.uuid4().hex[:10].upper()}"
            ret_qty = random.randint(1, 2)
            ret_amt = round(sku_price_map[selected_sku] * ret_qty, 2)
            transactions.append({
                "transaction_id": ret_id,
                "timestamp": ret_time.strftime("%Y-%m-%d %H:%M:%S"),
                "store_id": base_store,
                "transaction_type": "RETURN",
                "triangle_id": contractor_triangle_id,
                "payment_token": contractor_card,
                "sku": selected_sku,
                "quantity": ret_qty,
                "amount": ret_amt,
                "is_receipted": True
            })
            labels.append({"transaction_id": ret_id, "is_fraud": 0, "scenario": "CONTRACTOR"})

    # ---------------------------------------------------------
    # 3. ORGANIZED RETAIL CRIME (ORC) SYNDICATE: "The 401 Tender Washers"
    # Shared payment token across multiple unlinked/disposable shoppers,
    # hitting multiple stores across Peel/Halton/Toronto with unreceipted returns
    # of high-value tools to wash for gift cards / cash.
    # ---------------------------------------------------------
    orc_rings = [
        {"ring_id": "ORC_RING_ALPHA", "shared_token": "TOK_VISA_SYNDICATE_A", "stores": ["STORE_106", "STORE_104", "STORE_103", "STORE_101"]},
        {"ring_id": "ORC_RING_BETA", "shared_token": "TOK_MC_SYNDICATE_B", "stores": ["STORE_107", "STORE_108", "STORE_109", "STORE_110"]},
    ]

    for ring in orc_rings:
        ring_token = ring["shared_token"]
        target_stores = ring["stores"]
        base_day = random.randint(10, 18)
        
        # 3 straw shoppers in this syndicate
        for member_idx in range(3):
            # Member uses no loyalty OR rotates disposable loyalty accounts
            member_loyalty = f"TRI_BURNER_{random.randint(5000, 9999)}" if random.random() < 0.3 else None
            
            # The member executes returns across the corridor over a 48-hour burst
            for store_idx, store_id in enumerate(target_stores):
                burst_time = START_DATE + timedelta(
                    days=base_day,
                    hours=10 + (store_idx * 2) + member_idx,
                    minutes=random.randint(5, 50)
                )
                ret_tx_id = f"TX_ORC_{uuid.uuid4().hex[:10].upper()}"
                stolen_tool = random.choice(high_risk_skus)
                qty = random.randint(1, 2)
                amt = round(sku_price_map[stolen_tool] * qty, 2)
                
                transactions.append({
                    "transaction_id": ret_tx_id,
                    "timestamp": burst_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "store_id": store_id,
                    "transaction_type": "RETURN",
                    "triangle_id": member_loyalty,
                    "payment_token": ring_token,
                    "sku": stolen_tool,
                    "quantity": qty,
                    "amount": amt,
                    "is_receipted": False  # Crucial ORC operational signal
                })
                labels.append({"transaction_id": ret_tx_id, "is_fraud": 1, "scenario": ring["ring_id"]})

    df_tx = pd.DataFrame(transactions).sort_values("timestamp").reset_index(drop=True)
    df_labels = pd.DataFrame(labels)

    df_tx.to_csv(RAW_DATA_DIR / "transactions.csv", index=False)
    df_labels.to_csv(RAW_DATA_DIR / "ground_truth_labels.csv", index=False)
    
    return df_tx, df_labels


def main() -> None:
    print("=" * 60)
    print("GENERATING SYNTHETIC CANADIAN TIRE DATASET")
    print("=" * 60)
    
    stores_df = generate_stores()
    print(f"[OK] Generated {len(stores_df)} Stores -> {RAW_DATA_DIR / 'stores.csv'}")
    
    products_df = generate_products()
    print(f"[OK] Generated {len(products_df)} Products -> {RAW_DATA_DIR / 'products.csv'}")
    
    tx_df, labels_df = generate_transactions(stores_df, products_df)
    print(f"[OK] Generated {len(tx_df)} Total Transactions -> {RAW_DATA_DIR / 'transactions.csv'}")
    print(f"[OK] Saved Ground-Truth Evaluation Labels -> {RAW_DATA_DIR / 'ground_truth_labels.csv'}")
    
    # Validation summary
    fraud_count = labels_df["is_fraud"].sum()
    fraud_pct = (fraud_count / len(tx_df)) * 100
    print("\nDataset Summary:")
    print(f"  Total records: {len(tx_df):,}")
    print(f"  Normal / Contractor records: {len(tx_df) - fraud_count:,}")
    print(f"  ORC Fraud records: {fraud_count:,} ({fraud_pct:.2f}%)")
    print(f"  Missing Triangle IDs (Anonymous): {tx_df['triangle_id'].isna().sum():,} ({tx_df['triangle_id'].isna().mean()*100:.1f}%)")
    print("=" * 60)


if __name__ == "__main__":
    main()