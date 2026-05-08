// src/screens/algo_trading/StrategyBuilderPanel.h
#pragma once
#include "services/algo_trading/AlgoTradingTypes.h"

#include <QComboBox>
#include <QDoubleSpinBox>
#include <QGridLayout>
#include <QJsonArray>
#include <QLabel>
#include <QLineEdit>
#include <QPushButton>
#include <QSplitter>
#include <QVBoxLayout>
#include <QWidget>

namespace fincept::screens {

/// Strategy builder — QSplitter workstation layout.
/// Left: strategy editor (definition + conditions + risk).
/// Right: backtest params + Quant Lab-style KPI result cards.
class StrategyBuilderPanel : public QWidget {
    Q_OBJECT
  public:
    explicit StrategyBuilderPanel(QWidget* parent = nullptr);
    void load_strategy(const fincept::services::algo::AlgoStrategy& strategy);

  private slots:
    void on_save();
    void on_backtest();
    void on_backtest_result(const QJsonObject& data);
    void on_error(const QString& context, const QString& msg);

  private:
    void build_ui();
    void connect_service();
    QWidget* build_left_pane();
    QWidget* build_right_pane();
    QWidget* build_condition_row(QWidget* parent);
    QJsonObject gather_polymarket_bot_config() const;
    void load_polymarket_bot_config(const QJsonObject& cfg);
    void display_backtest_result(const QJsonObject& data);
    void clear_results();

    // Left pane — strategy editor
    QLineEdit*       name_edit_               = nullptr;
    QLineEdit*       desc_edit_               = nullptr;
    QComboBox*       market_type_combo_       = nullptr;
    QLabel*          market_id_label_         = nullptr;
    QLineEdit*       market_id_edit_          = nullptr;
    QLabel*          symbol_label_            = nullptr;
    QLineEdit*       symbol_edit_             = nullptr;
    QComboBox*       timeframe_combo_         = nullptr;
    QWidget*         polymarket_config_widget_ = nullptr;
    QComboBox*       poly_strategy_mode_combo_ = nullptr;
    QDoubleSpinBox*  poly_scan_interval_spin_ = nullptr;
    QDoubleSpinBox*  poly_max_candidates_spin_ = nullptr;
    QComboBox*       poly_sort_by_combo_ = nullptr;
    QDoubleSpinBox*  poly_min_volume_spin_ = nullptr;
    QDoubleSpinBox*  poly_min_liquidity_spin_ = nullptr;
    QDoubleSpinBox*  poly_max_spread_spin_ = nullptr;
    QDoubleSpinBox*  poly_min_depth_spin_ = nullptr;
    QDoubleSpinBox*  poly_min_price_spin_ = nullptr;
    QDoubleSpinBox*  poly_max_price_spin_ = nullptr;
    QLineEdit*       poly_excluded_categories_edit_ = nullptr;
    QLineEdit*       poly_excluded_tags_edit_ = nullptr;
    QDoubleSpinBox*  poly_min_expiry_spin_ = nullptr;
    QDoubleSpinBox*  poly_min_edge_spin_ = nullptr;
    QDoubleSpinBox*  poly_confidence_spin_ = nullptr;
    QDoubleSpinBox*  poly_momentum_weight_spin_ = nullptr;
    QDoubleSpinBox*  poly_volatility_penalty_spin_ = nullptr;
    QDoubleSpinBox*  poly_imbalance_weight_spin_ = nullptr;
    QDoubleSpinBox*  poly_liquidity_weight_spin_ = nullptr;
    QDoubleSpinBox*  poly_spread_penalty_spin_ = nullptr;
    QDoubleSpinBox*  poly_order_size_spin_ = nullptr;
    QDoubleSpinBox*  poly_max_order_spin_ = nullptr;
    QDoubleSpinBox*  poly_max_exposure_spin_ = nullptr;
    QDoubleSpinBox*  poly_daily_loss_spin_ = nullptr;
    QDoubleSpinBox*  poly_max_positions_spin_ = nullptr;
    QDoubleSpinBox*  poly_cooldown_spin_ = nullptr;
    QDoubleSpinBox*  poly_stop_loss_spin_ = nullptr;
    QDoubleSpinBox*  poly_take_profit_spin_ = nullptr;
    QDoubleSpinBox*  poly_trailing_stop_spin_ = nullptr;
    QComboBox*       entry_logic_combo_       = nullptr;
    QComboBox*       exit_logic_combo_        = nullptr;
    QDoubleSpinBox*  stop_loss_spin_          = nullptr;
    QDoubleSpinBox*  take_profit_spin_        = nullptr;
    QDoubleSpinBox*  trailing_stop_spin_      = nullptr;
    QVBoxLayout*     entry_conditions_layout_ = nullptr;
    QVBoxLayout*     exit_conditions_layout_  = nullptr;

    // Right pane — backtest
    QLabel*          bt_symbol_label_        = nullptr;
    QLineEdit*       bt_symbol_              = nullptr;
    QDoubleSpinBox*  bt_capital_             = nullptr;
    QLineEdit*       bt_start_date_          = nullptr;
    QLineEdit*       bt_end_date_            = nullptr;
    QLabel*          status_label_           = nullptr;
    QVBoxLayout*     results_layout_         = nullptr;
    QLabel*          bt_empty_label_         = nullptr;

    // KPI card value labels — updated in display_backtest_result()
    QLabel* kpi_total_return_val_  = nullptr;
    QLabel* kpi_total_return_sub_  = nullptr;
    QLabel* kpi_sharpe_val_        = nullptr;
    QLabel* kpi_sharpe_sub_        = nullptr;
    QLabel* kpi_max_dd_val_        = nullptr;
    QLabel* kpi_max_dd_sub_        = nullptr;
    QLabel* kpi_win_rate_val_      = nullptr;
    QLabel* kpi_win_rate_sub_      = nullptr;
    QLabel* kpi_trades_val_        = nullptr;
    QLabel* kpi_trades_sub_        = nullptr;
    QLabel* kpi_profit_factor_val_ = nullptr;
    QLabel* kpi_profit_factor_sub_ = nullptr;
    QWidget* kpi_grid_widget_      = nullptr; // hidden until first result
    QString current_strategy_id_;

    void sync_market_type_ui();
};

} // namespace fincept::screens
