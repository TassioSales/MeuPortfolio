from sqlalchemy.orm import Session
from app.models import models
from app.schemas import schemas
from app.services import market_service
from app.core.logger import log

async def calculate_portfolio(db: Session):
    try:
        log.info("Calculating portfolio positions...")
        assets = db.query(models.Asset).all()
        portfolio = []
        
        for asset in assets:
            transactions = asset.transactions
            if not transactions:
                log.debug(f"No transactions for asset {asset.ticker}")
                continue
                
            total_quantity = 0.0
            total_invested = 0.0
            
            for tx in transactions:
                if tx.transaction_type == models.TransactionType.BUY:
                    total_quantity += tx.quantity
                    total_invested += (tx.quantity * tx.price_per_unit) + tx.fees
                elif tx.transaction_type == models.TransactionType.SELL:
                    if total_quantity > 0:
                        average_price_before_sell = total_invested / total_quantity
                        total_quantity -= tx.quantity
                        total_invested -= (tx.quantity * average_price_before_sell)
            
            if total_quantity > 0:
                average_price = total_invested / total_quantity
                log.debug(f"Fetching market price for {asset.ticker}")
                current_price = await market_service.get_market_price(asset.ticker, asset.asset_type.value)
                current_value = current_price * total_quantity
                profit_loss = current_value - total_invested
                profit_loss_percentage = (profit_loss / total_invested) * 100 if total_invested > 0 else 0
                
                portfolio.append(schemas.PortfolioPosition(
                    asset=schemas.AssetOut.model_validate(asset),
                    total_quantity=total_quantity,
                    average_price=average_price,
                    current_price=current_price,
                    current_value=current_value,
                    total_invested=total_invested,
                    profit_loss=profit_loss,
                    profit_loss_percentage=profit_loss_percentage
                ))
        
        log.info(f"Portfolio calculation complete. Found {len(portfolio)} positions.")
        return portfolio
    except Exception as e:
        log.error(f"Error calculating portfolio: {e}", exc_info=True)
        raise e
