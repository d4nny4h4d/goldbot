"""MT5 order execution — place, modify, and close trades."""

import logging
from datetime import datetime, timezone

import MetaTrader5 as mt5

logger = logging.getLogger(__name__)


class MT5Executor:
    """Handles all order operations via the MT5 Python API."""

    def __init__(self, symbol: str = "XAUUSD"):
        self.symbol = symbol

    def _get_filling_mode(self) -> int:
        """Detect the filling mode supported by broker for this symbol."""
        info = mt5.symbol_info(self.symbol)
        if info is None:
            return mt5.ORDER_FILLING_IOC

        filling = info.filling_mode
        # Bit flags: FOK=1, IOC=2, RETURN=4
        if filling & 1:  # FOK supported
            return mt5.ORDER_FILLING_FOK
        if filling & 2:  # IOC supported
            return mt5.ORDER_FILLING_IOC
        return mt5.ORDER_FILLING_RETURN

    # ── Market orders ────────────────────────────────────────────────────────

    def open_trade(
        self,
        direction: str,
        lots: float,
        sl_price: float,
        tp_price: float,
        comment: str = "GoldBot",
        magic: int = 123456,
    ) -> dict | None:
        """Place a market order with SL and TP.

        Args:
            direction: "buy" or "sell"
            lots: Position size
            sl_price: Stop loss price
            tp_price: Take profit price
            comment: Order comment
            magic: Magic number for identifying bot trades

        Returns:
            dict with order details on success, None on failure
        """
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            logger.error("Cannot get tick for %s", self.symbol)
            return None

        if direction == "buy":
            order_type = mt5.ORDER_TYPE_BUY
            price = tick.ask
        elif direction == "sell":
            order_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
        else:
            logger.error("Invalid direction: %s", direction)
            return None

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": lots,
            "type": order_type,
            "price": price,
            "sl": round(sl_price, 2),
            "tp": round(tp_price, 2),
            "deviation": 20,  # max slippage in points
            "magic": magic,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._get_filling_mode(),
        }

        result = mt5.order_send(request)
        if result is None:
            logger.error("order_send returned None — MT5 error: %s", mt5.last_error())
            return None

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(
                "Order failed — retcode: %s, comment: %s",
                result.retcode, result.comment,
            )
            return None

        logger.info(
            "ORDER OPENED: %s %s %.2f lots @ %.2f | SL: %.2f | TP: %.2f | Ticket: %s",
            direction.upper(), self.symbol, lots, result.price,
            sl_price, tp_price, result.order,
        )

        return {
            "ticket": result.order,
            "direction": direction,
            "symbol": self.symbol,
            "lots": lots,
            "entry_price": result.price,
            "sl": sl_price,
            "tp": tp_price,
            "time": datetime.now(timezone.utc),
            "comment": comment,
        }

    # ── Close positions ──────────────────────────────────────────────────────

    def close_trade(self, ticket: int, comment: str = "GoldBot close") -> bool:
        """Close a specific position by ticket number."""
        position = mt5.positions_get(ticket=ticket)
        if not position:
            logger.warning("Position %s not found", ticket)
            return False

        pos = position[0]
        tick = mt5.symbol_info_tick(pos.symbol)
        if tick is None:
            logger.error("Cannot get tick for %s", pos.symbol)
            return False

        # Opposite direction to close
        if pos.type == mt5.ORDER_TYPE_BUY:
            close_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
        else:
            close_type = mt5.ORDER_TYPE_BUY
            price = tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": close_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": pos.magic,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._get_filling_mode(),
        }

        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            error = result.comment if result else mt5.last_error()
            logger.error("Close failed for ticket %s: %s", ticket, error)
            return False

        logger.info("POSITION CLOSED: Ticket %s @ %.2f", ticket, result.price)
        return True

    def close_all(self, comment: str = "GoldBot close all", magic: int = 0) -> int:
        """Close all open positions belonging to this bot (filtered by magic number)."""
        positions = mt5.positions_get()
        if not positions:
            return 0

        own = [p for p in positions if p.magic == magic] if magic else list(positions)
        closed = 0
        for pos in own:
            if self.close_trade(pos.ticket, comment):
                closed += 1
        logger.info("Closed %d/%d positions (magic=%d)", closed, len(own), magic)
        return closed

    # ── Modify SL/TP ─────────────────────────────────────────────────────────

    def modify_sl_tp(
        self, ticket: int, new_sl: float | None = None, new_tp: float | None = None
    ) -> bool:
        """Modify the SL and/or TP of an open position."""
        position = mt5.positions_get(ticket=ticket)
        if not position:
            logger.warning("Position %s not found for modification", ticket)
            return False

        pos = position[0]
        sl = round(new_sl, 2) if new_sl is not None else pos.sl
        tp = round(new_tp, 2) if new_tp is not None else pos.tp

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": pos.symbol,
            "position": ticket,
            "sl": sl,
            "tp": tp,
        }

        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            error = result.comment if result else mt5.last_error()
            logger.error("Modify failed for ticket %s: %s", ticket, error)
            return False

        logger.info("MODIFIED: Ticket %s — SL: %.2f, TP: %.2f", ticket, sl, tp)
        return True

    # ── Position queries ─────────────────────────────────────────────────────

    def get_open_positions(self) -> list[dict]:
        """Get all open positions as dicts."""
        positions = mt5.positions_get()
        if not positions:
            return []

        result = []
        for pos in positions:
            result.append({
                "ticket": pos.ticket,
                "symbol": pos.symbol,
                "direction": "buy" if pos.type == mt5.ORDER_TYPE_BUY else "sell",
                "lots": pos.volume,
                "entry_price": pos.price_open,
                "current_price": pos.price_current,
                "sl": pos.sl,
                "tp": pos.tp,
                "profit": pos.profit,
                "profit_pct": (pos.profit / max(1, pos.price_open * pos.volume * 100)) * 100,
                "swap": pos.swap,
                "magic": pos.magic,
                "comment": pos.comment,
                "time": datetime.fromtimestamp(pos.time, tz=timezone.utc),
            })
        return result

    def get_history(self, days: int = 30) -> list[dict]:
        """Get closed trade history."""
        from_date = datetime.now(timezone.utc) - __import__("datetime").timedelta(days=days)
        to_date = datetime.now(timezone.utc)

        deals = mt5.history_deals_get(from_date, to_date)
        if not deals:
            return []

        result = []
        for deal in deals:
            if deal.entry == mt5.DEAL_ENTRY_OUT:  # only closing deals
                result.append({
                    "ticket": deal.ticket,
                    "order": deal.order,
                    "symbol": deal.symbol,
                    "direction": "buy" if deal.type == mt5.DEAL_TYPE_BUY else "sell",
                    "lots": deal.volume,
                    "price": deal.price,
                    "profit": deal.profit,
                    "commission": deal.commission,
                    "swap": deal.swap,
                    "magic": deal.magic,
                    "comment": deal.comment,
                    "time": datetime.fromtimestamp(deal.time, tz=timezone.utc),
                })
        return result
