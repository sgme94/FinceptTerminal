// src/screens/algo_trading/StrategyBuilderPanel.cpp
#include "screens/algo_trading/StrategyBuilderPanel.h"

#include "core/logging/Logger.h"
#include "services/algo_trading/AlgoTradingService.h"
#include "services/file_manager/FileManagerService.h"
#include "ui/theme/Theme.h"

#include <QFile>
#include <QFileInfo>
#include <QGridLayout>
#include <QHBoxLayout>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QRegularExpression>
#include <QScrollArea>
#include <QSignalBlocker>
#include <QSplitter>
#include <QUuid>

// ── Shared style helpers ────────────────────────────────────────────────────

namespace {

inline QString kMonoFont() {
    return QString("font-family: %1;").arg(fincept::ui::fonts::DATA_FAMILY);
}
inline QString kLabelStyle() {
    return QString("color: %1; font-size: %2px; font-weight: 700; letter-spacing: 0.5px; %3"
                   "background: transparent; border: none;")
        .arg(fincept::ui::colors::TEXT_SECONDARY())
        .arg(fincept::ui::fonts::TINY)
        .arg(kMonoFont());
}
inline QString kSectionLabel() {
    return QString("color: %1; font-size: %2px; font-weight: 700; letter-spacing: 0.5px; %3"
                   "background: transparent; border: none;")
        .arg(fincept::ui::colors::AMBER())
        .arg(fincept::ui::fonts::TINY)
        .arg(kMonoFont());
}
inline QString kInputStyle() {
    return QString("QLineEdit { background: %1; border: 1px solid %2; color: %3; padding: 4px 8px;"
                   " font-size: %4px; %5 }"
                   "QLineEdit:focus { border-color: %6; }")
        .arg(fincept::ui::colors::BG_SURFACE(), fincept::ui::colors::BORDER_DIM(),
             fincept::ui::colors::TEXT_PRIMARY())
        .arg(fincept::ui::fonts::SMALL)
        .arg(kMonoFont())
        .arg(fincept::ui::colors::BORDER_BRIGHT());
}
inline QString kComboStyle() {
    return QString("QComboBox { background: %1; color: %2; border: 1px solid %3; padding: 4px 8px;"
                   " font-size: %4px; %5 }"
                   "QComboBox::drop-down { border: none; }"
                   "QComboBox QAbstractItemView { background: %1; color: %2; border: 1px solid %3;"
                   " selection-background-color: %6; %5 }")
        .arg(fincept::ui::colors::BG_SURFACE(), fincept::ui::colors::TEXT_PRIMARY(),
             fincept::ui::colors::BORDER_DIM())
        .arg(fincept::ui::fonts::SMALL)
        .arg(kMonoFont())
        .arg(fincept::ui::colors::BG_HOVER());
}
inline QString kSpinStyle() {
    return QString("QDoubleSpinBox { background: %1; color: %2; border: 1px solid %3; padding: 4px 8px;"
                   " font-size: %4px; %5 }"
                   "QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width: 14px; }")
        .arg(fincept::ui::colors::BG_SURFACE(), fincept::ui::colors::TEXT_PRIMARY(),
             fincept::ui::colors::BORDER_DIM())
        .arg(fincept::ui::fonts::SMALL)
        .arg(kMonoFont());
}

} // namespace

namespace fincept::screens {

using namespace fincept::services::algo;

// ── gather_from_layout ──────────────────────────────────────────────────────

static QJsonArray gather_from_layout(QVBoxLayout* layout) {
    QJsonArray arr;
    for (int i = 0; i < layout->count(); ++i) {
        auto* item = layout->itemAt(i);
        auto* row  = item ? item->widget() : nullptr;
        if (!row) continue;
        auto* ind_combo   = qobject_cast<QComboBox*>(row->property("ind_combo").value<QObject*>());
        auto* field_combo = qobject_cast<QComboBox*>(row->property("field_combo").value<QObject*>());
        auto* op_combo    = qobject_cast<QComboBox*>(row->property("op_combo").value<QObject*>());
        auto* val_spin    = qobject_cast<QDoubleSpinBox*>(row->property("val_spin").value<QObject*>());
        if (!ind_combo || !field_combo || !op_combo || !val_spin) continue;
        QJsonObject cond;
        cond["indicator"] = ind_combo->currentData().toString();
        cond["field"]     = field_combo->currentText();
        cond["operator"]  = op_combo->currentText();
        cond["value"]     = val_spin->value();
        cond["params"]    = QJsonObject{};
        arr.append(cond);
    }
    return arr;
}

static QJsonArray split_csv_to_json(const QString& text) {
    QJsonArray arr;
    for (const auto& part : text.split(',', Qt::SkipEmptyParts)) {
        const QString trimmed = part.trimmed();
        if (!trimmed.isEmpty())
            arr.append(trimmed);
    }
    return arr;
}

static QString join_json_strings(const QJsonArray& arr) {
    QStringList values;
    for (const auto& value : arr) {
        const QString text = value.toString().trimmed();
        if (!text.isEmpty())
            values.append(text);
    }
    return values.join(", ");
}

static double json_number(const QJsonObject& obj, const QString& key, double fallback) {
    return obj.contains(key) ? obj.value(key).toDouble(fallback) : fallback;
}

// ── Constructor ─────────────────────────────────────────────────────────────

StrategyBuilderPanel::StrategyBuilderPanel(QWidget* parent) : QWidget(parent) {
    build_ui();
    connect_service();
    LOG_INFO("AlgoTrading", "StrategyBuilderPanel constructed");
}

// ── Service connections ─────────────────────────────────────────────────────

void StrategyBuilderPanel::connect_service() {
    auto& svc = AlgoTradingService::instance();
    connect(&svc, &AlgoTradingService::strategy_saved, this, [this](const QString& id) {
        current_strategy_id_ = id;
        if (status_label_)
            status_label_->setText(QString("Strategy saved: %1").arg(id));
        status_label_->setStyleSheet(
            QString("color: %1; font-size: %2px; %3 background: transparent; border: none;")
                .arg(fincept::ui::colors::POSITIVE())
                .arg(fincept::ui::fonts::SMALL)
                .arg(kMonoFont()));
    });
    connect(&svc, &AlgoTradingService::backtest_result, this,
            &StrategyBuilderPanel::on_backtest_result);
    connect(&svc, &AlgoTradingService::error_occurred, this,
            &StrategyBuilderPanel::on_error);
}

// ── Condition row ───────────────────────────────────────────────────────────

QWidget* StrategyBuilderPanel::build_condition_row(QWidget* parent) {
    auto* row = new QWidget(parent);
    row->setStyleSheet(QString("background: %1; border: 1px solid %2;")
                           .arg(fincept::ui::colors::BG_SURFACE(), fincept::ui::colors::BORDER_DIM()));
    auto* hl = new QHBoxLayout(row);
    hl->setContentsMargins(6, 4, 6, 4);
    hl->setSpacing(4);

    auto* ind_combo = new QComboBox(row);
    ind_combo->setStyleSheet(kComboStyle());
    ind_combo->setFixedHeight(28);
    ind_combo->setMinimumWidth(120);
    const auto indicators = algo_indicators();
    for (const auto& ind : indicators)
        ind_combo->addItem(ind.label, ind.id);

    auto* field_combo = new QComboBox(row);
    field_combo->setStyleSheet(kComboStyle());
    field_combo->setFixedHeight(28);
    field_combo->setMinimumWidth(90);

    connect(ind_combo, QOverload<int>::of(&QComboBox::currentIndexChanged), row,
            [field_combo, indicators](int idx) {
                field_combo->clear();
                if (idx >= 0 && idx < indicators.size())
                    field_combo->addItems(indicators[idx].fields);
            });

    auto* op_combo = new QComboBox(row);
    op_combo->setStyleSheet(kComboStyle());
    op_combo->setFixedHeight(28);
    op_combo->setMinimumWidth(100);
    op_combo->addItems(algo_operators());

    auto* val_spin = new QDoubleSpinBox(row);
    val_spin->setStyleSheet(kSpinStyle());
    val_spin->setFixedHeight(28);
    val_spin->setMinimumWidth(90);
    val_spin->setRange(-1e9, 1e9);
    val_spin->setDecimals(4);
    val_spin->setValue(0);

    auto* rm_btn = new QPushButton("X", row);
    rm_btn->setFixedSize(28, 28);
    rm_btn->setCursor(Qt::PointingHandCursor);
    rm_btn->setStyleSheet(
        QString("QPushButton { background: transparent; color: %1; border: 1px solid %2;"
                " font-size: %3px; font-weight: 700; %4 }"
                "QPushButton:hover { color: %5; border-color: %5; }")
            .arg(fincept::ui::colors::TEXT_TERTIARY(), fincept::ui::colors::BORDER_DIM())
            .arg(fincept::ui::fonts::TINY)
            .arg(kMonoFont())
            .arg(fincept::ui::colors::NEGATIVE()));
    connect(rm_btn, &QPushButton::clicked, row, [row]() { row->deleteLater(); });

    hl->addWidget(ind_combo);
    hl->addWidget(field_combo);
    hl->addWidget(op_combo);
    hl->addWidget(val_spin);
    hl->addWidget(rm_btn);

    if (ind_combo->count() > 0)
        emit ind_combo->currentIndexChanged(0);

    row->setProperty("ind_combo",   QVariant::fromValue(static_cast<QObject*>(ind_combo)));
    row->setProperty("field_combo", QVariant::fromValue(static_cast<QObject*>(field_combo)));
    row->setProperty("op_combo",    QVariant::fromValue(static_cast<QObject*>(op_combo)));
    row->setProperty("val_spin",    QVariant::fromValue(static_cast<QObject*>(val_spin)));

    return row;
}

// ── Left pane: strategy editor ──────────────────────────────────────────────

QWidget* StrategyBuilderPanel::build_left_pane() {
    auto* pane = new QWidget(this);
    pane->setStyleSheet(
        QString("background: %1; border-right: 1px solid %2;")
            .arg(fincept::ui::colors::BG_BASE(), fincept::ui::colors::BORDER_DIM()));

    auto* root_layout = new QVBoxLayout(pane);
    root_layout->setContentsMargins(0, 0, 0, 0);
    root_layout->setSpacing(0);

    auto* scroll = new QScrollArea(pane);
    scroll->setWidgetResizable(true);
    scroll->setFrameShape(QFrame::NoFrame);
    scroll->setStyleSheet(
        QString("QScrollArea { background: %1; border: none; }"
                "QScrollBar:vertical { background: %1; width: 6px; }"
                "QScrollBar::handle:vertical { background: %2; }"
                "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")
            .arg(fincept::ui::colors::BG_BASE(), fincept::ui::colors::BORDER_MED()));

    auto* content = new QWidget;
    content->setStyleSheet(QString("background: %1;").arg(fincept::ui::colors::BG_BASE()));
    auto* vl = new QVBoxLayout(content);
    vl->setContentsMargins(16, 12, 16, 12);
    vl->setSpacing(8);

    // ── Strategy Definition ─────────────────────────────────────────────────
    auto* id_sec = new QLabel("STRATEGY DEFINITION", content);
    id_sec->setStyleSheet(kSectionLabel());
    vl->addWidget(id_sec);

    auto* name_lbl = new QLabel("NAME", content);
    name_lbl->setStyleSheet(kLabelStyle());
    vl->addWidget(name_lbl);
    name_edit_ = new QLineEdit(content);
    name_edit_->setPlaceholderText("My Strategy");
    name_edit_->setStyleSheet(kInputStyle());
    name_edit_->setFixedHeight(30);
    vl->addWidget(name_edit_);

    auto* desc_lbl = new QLabel("DESCRIPTION", content);
    desc_lbl->setStyleSheet(kLabelStyle());
    vl->addWidget(desc_lbl);
    desc_edit_ = new QLineEdit(content);
    desc_edit_->setPlaceholderText("Strategy description...");
    desc_edit_->setStyleSheet(kInputStyle());
    desc_edit_->setFixedHeight(30);
    vl->addWidget(desc_edit_);

    auto* market_type_lbl = new QLabel("MARKET TYPE", content);
    market_type_lbl->setStyleSheet(kLabelStyle());
    vl->addWidget(market_type_lbl);
    market_type_combo_ = new QComboBox(content);
    market_type_combo_->addItem("Equity", "equity");
    market_type_combo_->addItem("Polymarket", "polymarket");
    market_type_combo_->setStyleSheet(kComboStyle());
    market_type_combo_->setFixedHeight(30);
    vl->addWidget(market_type_combo_);

    market_id_label_ = new QLabel("MARKET ID", content);
    market_id_label_->setStyleSheet(kLabelStyle());
    vl->addWidget(market_id_label_);
    market_id_edit_ = new QLineEdit(content);
    market_id_edit_->setPlaceholderText("Optional condition ID");
    market_id_edit_->setStyleSheet(kInputStyle());
    market_id_edit_->setFixedHeight(30);
    vl->addWidget(market_id_edit_);

    symbol_label_ = new QLabel("SYMBOL", content);
    symbol_label_->setStyleSheet(kLabelStyle());
    vl->addWidget(symbol_label_);
    symbol_edit_ = new QLineEdit(content);
    symbol_edit_->setPlaceholderText("RELIANCE.NS or Polymarket token ID");
    symbol_edit_->setStyleSheet(kInputStyle());
    symbol_edit_->setFixedHeight(30);
    connect(symbol_edit_, &QLineEdit::textChanged, this, [this](const QString& text) {
        if (bt_symbol_)
            bt_symbol_->setText(text);
    });
    vl->addWidget(symbol_edit_);

    auto* tf_lbl = new QLabel("TIMEFRAME", content);
    tf_lbl->setStyleSheet(kLabelStyle());
    vl->addWidget(tf_lbl);
    timeframe_combo_ = new QComboBox(content);
    timeframe_combo_->addItems(algo_timeframes());
    timeframe_combo_->setStyleSheet(kComboStyle());
    timeframe_combo_->setFixedHeight(30);
    vl->addWidget(timeframe_combo_);

    connect(market_type_combo_, QOverload<int>::of(&QComboBox::currentIndexChanged), this,
            [this](int) { sync_market_type_ui(); });

    polymarket_config_widget_ = new QWidget(content);
    polymarket_config_widget_->setStyleSheet(QString("background: %1; border: 1px solid %2;")
                                                 .arg(fincept::ui::colors::BG_SURFACE(),
                                                      fincept::ui::colors::BORDER_DIM()));
    auto* poly_vl = new QVBoxLayout(polymarket_config_widget_);
    poly_vl->setContentsMargins(8, 8, 8, 8);
    poly_vl->setSpacing(6);

    auto* poly_title = new QLabel("POLYMARKET PAPER BOT", polymarket_config_widget_);
    poly_title->setStyleSheet(kSectionLabel());
    poly_vl->addWidget(poly_title);

    auto* poly_grid_widget = new QWidget(polymarket_config_widget_);
    auto* poly_grid = new QGridLayout(poly_grid_widget);
    poly_grid->setContentsMargins(0, 0, 0, 0);
    poly_grid->setHorizontalSpacing(8);
    poly_grid->setVerticalSpacing(6);
    int poly_row = 0;

    auto add_poly_label = [&](const QString& label, QWidget* input) {
        auto* lbl = new QLabel(label, poly_grid_widget);
        lbl->setStyleSheet(kLabelStyle());
        poly_grid->addWidget(lbl, poly_row, 0);
        poly_grid->addWidget(input, poly_row, 1);
        ++poly_row;
    };
    auto make_poly_spin = [&](double min, double max, double value, int decimals = 2) {
        auto* spin = new QDoubleSpinBox(poly_grid_widget);
        spin->setStyleSheet(kSpinStyle());
        spin->setFixedHeight(28);
        spin->setRange(min, max);
        spin->setDecimals(decimals);
        spin->setValue(value);
        return spin;
    };

    poly_strategy_mode_combo_ = new QComboBox(poly_grid_widget);
    poly_strategy_mode_combo_->addItem("Auto Scan", "auto_scan");
    poly_strategy_mode_combo_->setStyleSheet(kComboStyle());
    poly_strategy_mode_combo_->setFixedHeight(28);
    add_poly_label("STRATEGY MODE", poly_strategy_mode_combo_);

    poly_scan_interval_spin_ = make_poly_spin(5, 3600, 60, 0);
    add_poly_label("SCAN INTERVAL SEC", poly_scan_interval_spin_);
    poly_max_candidates_spin_ = make_poly_spin(1, 200, 20, 0);
    add_poly_label("MAX CANDIDATES", poly_max_candidates_spin_);

    poly_sort_by_combo_ = new QComboBox(poly_grid_widget);
    poly_sort_by_combo_->addItem("Volume", "volume");
    poly_sort_by_combo_->addItem("Liquidity", "liquidity");
    poly_sort_by_combo_->addItem("Price", "price");
    poly_sort_by_combo_->setStyleSheet(kComboStyle());
    poly_sort_by_combo_->setFixedHeight(28);
    add_poly_label("SORT BY", poly_sort_by_combo_);

    poly_min_volume_spin_ = make_poly_spin(0, 100000000, 1000, 0);
    add_poly_label("MIN VOLUME", poly_min_volume_spin_);
    poly_min_liquidity_spin_ = make_poly_spin(0, 100000000, 500, 0);
    add_poly_label("MIN LIQUIDITY", poly_min_liquidity_spin_);
    poly_max_spread_spin_ = make_poly_spin(0, 1, 0.05, 4);
    add_poly_label("MAX SPREAD", poly_max_spread_spin_);
    poly_min_depth_spin_ = make_poly_spin(0, 1000000, 10, 2);
    add_poly_label("MIN DEPTH", poly_min_depth_spin_);
    poly_min_price_spin_ = make_poly_spin(0, 1, 0.05, 4);
    add_poly_label("MIN PRICE", poly_min_price_spin_);
    poly_max_price_spin_ = make_poly_spin(0, 1, 0.95, 4);
    add_poly_label("MAX PRICE", poly_max_price_spin_);

    poly_excluded_categories_edit_ = new QLineEdit(poly_grid_widget);
    poly_excluded_categories_edit_->setStyleSheet(kInputStyle());
    poly_excluded_categories_edit_->setFixedHeight(28);
    add_poly_label("EXCLUDED CATEGORIES", poly_excluded_categories_edit_);
    poly_excluded_tags_edit_ = new QLineEdit(poly_grid_widget);
    poly_excluded_tags_edit_->setStyleSheet(kInputStyle());
    poly_excluded_tags_edit_->setFixedHeight(28);
    add_poly_label("EXCLUDED TAGS", poly_excluded_tags_edit_);

    poly_min_expiry_spin_ = make_poly_spin(0, 8760, 24, 0);
    add_poly_label("MIN EXPIRY HOURS", poly_min_expiry_spin_);
    poly_min_edge_spin_ = make_poly_spin(0, 1, 0.04, 4);
    add_poly_label("MIN EDGE", poly_min_edge_spin_);
    poly_confidence_spin_ = make_poly_spin(0, 1, 0.55, 4);
    add_poly_label("CONFIDENCE", poly_confidence_spin_);
    poly_momentum_weight_spin_ = make_poly_spin(0, 1, 0.20, 4);
    add_poly_label("MOMENTUM WEIGHT", poly_momentum_weight_spin_);
    poly_volatility_penalty_spin_ = make_poly_spin(0, 1, 0.15, 4);
    add_poly_label("VOL PENALTY", poly_volatility_penalty_spin_);
    poly_imbalance_weight_spin_ = make_poly_spin(0, 1, 0.20, 4);
    add_poly_label("IMBALANCE WEIGHT", poly_imbalance_weight_spin_);
    poly_liquidity_weight_spin_ = make_poly_spin(0, 1, 0.10, 4);
    add_poly_label("LIQUIDITY WEIGHT", poly_liquidity_weight_spin_);
    poly_spread_penalty_spin_ = make_poly_spin(0, 1, 0.20, 4);
    add_poly_label("SPREAD PENALTY", poly_spread_penalty_spin_);

    poly_order_size_spin_ = make_poly_spin(0, 1000000, 10, 2);
    add_poly_label("PAPER ORDER SIZE", poly_order_size_spin_);
    poly_max_order_spin_ = make_poly_spin(0, 1000000, 25, 2);
    add_poly_label("MAX ORDER USDC", poly_max_order_spin_);
    poly_max_exposure_spin_ = make_poly_spin(0, 1000000, 100, 2);
    add_poly_label("MAX EXPOSURE", poly_max_exposure_spin_);
    poly_daily_loss_spin_ = make_poly_spin(0, 1000000, 25, 2);
    add_poly_label("DAILY LOSS LIMIT", poly_daily_loss_spin_);
    poly_max_positions_spin_ = make_poly_spin(1, 1000, 5, 0);
    add_poly_label("MAX POSITIONS", poly_max_positions_spin_);
    poly_cooldown_spin_ = make_poly_spin(0, 1440, 10, 0);
    add_poly_label("COOLDOWN MIN", poly_cooldown_spin_);
    poly_stop_loss_spin_ = make_poly_spin(0, 100, 30, 2);
    add_poly_label("STOP LOSS %", poly_stop_loss_spin_);
    poly_take_profit_spin_ = make_poly_spin(0, 100, 50, 2);
    add_poly_label("TAKE PROFIT %", poly_take_profit_spin_);
    poly_trailing_stop_spin_ = make_poly_spin(0, 100, 0, 2);
    add_poly_label("TRAILING STOP %", poly_trailing_stop_spin_);

    poly_vl->addWidget(poly_grid_widget);
    vl->addWidget(polymarket_config_widget_);

    // ── Entry Conditions ────────────────────────────────────────────────────
    auto* entry_hdr = new QWidget(content);
    auto* entry_hdr_hl = new QHBoxLayout(entry_hdr);
    entry_hdr_hl->setContentsMargins(0, 8, 0, 0);
    entry_hdr_hl->setSpacing(8);
    auto* entry_lbl = new QLabel("ENTRY CONDITIONS", entry_hdr);
    entry_lbl->setStyleSheet(kSectionLabel());
    entry_hdr_hl->addWidget(entry_lbl);
    auto* entry_logic_lbl = new QLabel("Logic:", entry_hdr);
    entry_logic_lbl->setStyleSheet(kLabelStyle());
    entry_hdr_hl->addWidget(entry_logic_lbl);
    entry_logic_combo_ = new QComboBox(entry_hdr);
    entry_logic_combo_->addItems({"AND", "OR"});
    entry_logic_combo_->setStyleSheet(kComboStyle());
    entry_logic_combo_->setFixedHeight(26);
    entry_logic_combo_->setFixedWidth(80);
    entry_hdr_hl->addWidget(entry_logic_combo_);
    entry_hdr_hl->addStretch();
    vl->addWidget(entry_hdr);

    auto* entry_container = new QWidget(content);
    entry_conditions_layout_ = new QVBoxLayout(entry_container);
    entry_conditions_layout_->setContentsMargins(0, 0, 0, 0);
    entry_conditions_layout_->setSpacing(4);
    vl->addWidget(entry_container);

    auto* add_entry_btn = new QPushButton("+ ADD ENTRY CONDITION", content);
    add_entry_btn->setCursor(Qt::PointingHandCursor);
    add_entry_btn->setFixedHeight(28);
    add_entry_btn->setStyleSheet(
        QString("QPushButton { background: transparent; color: %1; border: 1px dashed %2;"
                " font-size: %3px; font-weight: 700; %4 }"
                "QPushButton:hover { color: %5; border-color: %5; }")
            .arg(fincept::ui::colors::TEXT_TERTIARY(), fincept::ui::colors::BORDER_DIM())
            .arg(fincept::ui::fonts::TINY)
            .arg(kMonoFont())
            .arg(fincept::ui::colors::AMBER()));
    connect(add_entry_btn, &QPushButton::clicked, this, [this, entry_container]() {
        entry_conditions_layout_->addWidget(build_condition_row(entry_container));
    });
    vl->addWidget(add_entry_btn);

    // ── Exit Conditions ─────────────────────────────────────────────────────
    auto* exit_hdr = new QWidget(content);
    auto* exit_hdr_hl = new QHBoxLayout(exit_hdr);
    exit_hdr_hl->setContentsMargins(0, 8, 0, 0);
    exit_hdr_hl->setSpacing(8);
    auto* exit_lbl = new QLabel("EXIT CONDITIONS", exit_hdr);
    exit_lbl->setStyleSheet(kSectionLabel());
    exit_hdr_hl->addWidget(exit_lbl);
    auto* exit_logic_lbl = new QLabel("Logic:", exit_hdr);
    exit_logic_lbl->setStyleSheet(kLabelStyle());
    exit_hdr_hl->addWidget(exit_logic_lbl);
    exit_logic_combo_ = new QComboBox(exit_hdr);
    exit_logic_combo_->addItems({"AND", "OR"});
    exit_logic_combo_->setStyleSheet(kComboStyle());
    exit_logic_combo_->setFixedHeight(26);
    exit_logic_combo_->setFixedWidth(80);
    exit_hdr_hl->addWidget(exit_logic_combo_);
    exit_hdr_hl->addStretch();
    vl->addWidget(exit_hdr);

    auto* exit_container = new QWidget(content);
    exit_conditions_layout_ = new QVBoxLayout(exit_container);
    exit_conditions_layout_->setContentsMargins(0, 0, 0, 0);
    exit_conditions_layout_->setSpacing(4);
    vl->addWidget(exit_container);

    auto* add_exit_btn = new QPushButton("+ ADD EXIT CONDITION", content);
    add_exit_btn->setCursor(Qt::PointingHandCursor);
    add_exit_btn->setFixedHeight(28);
    add_exit_btn->setStyleSheet(add_entry_btn->styleSheet());
    connect(add_exit_btn, &QPushButton::clicked, this, [this, exit_container]() {
        exit_conditions_layout_->addWidget(build_condition_row(exit_container));
    });
    vl->addWidget(add_exit_btn);

    // ── Risk Management ─────────────────────────────────────────────────────
    auto* risk_lbl = new QLabel("RISK MANAGEMENT", content);
    risk_lbl->setStyleSheet(kSectionLabel());
    vl->addWidget(risk_lbl);

    auto* risk_grid = new QWidget(content);
    auto* rgl = new QHBoxLayout(risk_grid);
    rgl->setContentsMargins(0, 0, 0, 0);
    rgl->setSpacing(12);

    auto make_risk_field = [&](const QString& label, double def_val) -> QDoubleSpinBox* {
        auto* col = new QWidget(risk_grid);
        auto* cvl = new QVBoxLayout(col);
        cvl->setContentsMargins(0, 0, 0, 0);
        cvl->setSpacing(2);
        auto* lbl = new QLabel(label, col);
        lbl->setStyleSheet(kLabelStyle());
        cvl->addWidget(lbl);
        auto* spin = new QDoubleSpinBox(col);
        spin->setStyleSheet(kSpinStyle());
        spin->setFixedHeight(30);
        spin->setRange(0.0, 100.0);
        spin->setDecimals(2);
        spin->setSuffix(" %");
        spin->setValue(def_val);
        spin->setSpecialValueText("DISABLED");
        cvl->addWidget(spin);
        rgl->addWidget(col);
        return spin;
    };

    stop_loss_spin_     = make_risk_field("STOP LOSS %",     0.0);
    take_profit_spin_   = make_risk_field("TAKE PROFIT %",   0.0);
    trailing_stop_spin_ = make_risk_field("TRAILING STOP %", 0.0);
    vl->addWidget(risk_grid);

    vl->addStretch();

    // ── Save button ─────────────────────────────────────────────────────────
    auto* save_btn = new QPushButton("SAVE STRATEGY", content);
    save_btn->setCursor(Qt::PointingHandCursor);
    save_btn->setFixedHeight(36);
    save_btn->setStyleSheet(
        QString("QPushButton { background: rgba(217,119,6,0.1); color: %1; border: 1px solid %1;"
                " font-size: %2px; font-weight: 700; %3 padding: 6px 24px; }"
                "QPushButton:hover { background: %1; color: %4; }")
            .arg(fincept::ui::colors::AMBER())
            .arg(fincept::ui::fonts::DATA)
            .arg(kMonoFont())
            .arg(fincept::ui::colors::BG_BASE()));
    connect(save_btn, &QPushButton::clicked, this, &StrategyBuilderPanel::on_save);
    vl->addWidget(save_btn);

    scroll->setWidget(content);
    root_layout->addWidget(scroll);
    return pane;
}

// ── Right pane: backtest workbench ──────────────────────────────────────────

QWidget* StrategyBuilderPanel::build_right_pane() {
    auto* pane = new QWidget(this);
    pane->setStyleSheet(QString("background: %1;").arg(fincept::ui::colors::BG_BASE()));

    auto* root_layout = new QVBoxLayout(pane);
    root_layout->setContentsMargins(0, 0, 0, 0);
    root_layout->setSpacing(0);

    auto* scroll = new QScrollArea(pane);
    scroll->setWidgetResizable(true);
    scroll->setFrameShape(QFrame::NoFrame);
    scroll->setStyleSheet(
        QString("QScrollArea { background: %1; border: none; }"
                "QScrollBar:vertical { background: %1; width: 6px; }"
                "QScrollBar::handle:vertical { background: %2; }"
                "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")
            .arg(fincept::ui::colors::BG_BASE(), fincept::ui::colors::BORDER_MED()));

    auto* content = new QWidget;
    content->setStyleSheet(QString("background: %1;").arg(fincept::ui::colors::BG_BASE()));
    auto* vl = new QVBoxLayout(content);
    vl->setContentsMargins(16, 12, 16, 12);
    vl->setSpacing(8);

    // ── Backtest Parameters ─────────────────────────────────────────────────
    auto* bt_sec = new QLabel("BACKTEST PARAMETERS", content);
    bt_sec->setStyleSheet(kSectionLabel());
    vl->addWidget(bt_sec);

    // 2×2 grid of params
    auto* params_grid = new QWidget(content);
    auto* params_gl   = new QGridLayout(params_grid);
    params_gl->setContentsMargins(0, 0, 0, 0);
    params_gl->setSpacing(8);

    auto make_param_col = [&](const QString& label_text, QWidget* input) -> QWidget* {
        auto* col = new QWidget(params_grid);
        auto* cvl = new QVBoxLayout(col);
        cvl->setContentsMargins(0, 0, 0, 0);
        cvl->setSpacing(2);
        auto* lbl = new QLabel(label_text, col);
        lbl->setStyleSheet(kLabelStyle());
        cvl->addWidget(lbl);
        input->setParent(col);
        cvl->addWidget(input);
        return col;
    };

    bt_symbol_ = new QLineEdit;
    bt_symbol_->setPlaceholderText("RELIANCE.NS");
    bt_symbol_->setReadOnly(true);
    bt_symbol_->setStyleSheet(kInputStyle());
    bt_symbol_->setFixedHeight(30);
    auto* symbol_col = new QWidget(params_grid);
    auto* symbol_cvl = new QVBoxLayout(symbol_col);
    symbol_cvl->setContentsMargins(0, 0, 0, 0);
    symbol_cvl->setSpacing(2);
    bt_symbol_label_ = new QLabel("SYMBOL", symbol_col);
    bt_symbol_label_->setStyleSheet(kLabelStyle());
    symbol_cvl->addWidget(bt_symbol_label_);
    bt_symbol_->setParent(symbol_col);
    symbol_cvl->addWidget(bt_symbol_);
    params_gl->addWidget(symbol_col, 0, 0);

    bt_capital_ = new QDoubleSpinBox;
    bt_capital_->setStyleSheet(kSpinStyle());
    bt_capital_->setFixedHeight(30);
    bt_capital_->setRange(100, 1e9);
    bt_capital_->setDecimals(0);
    bt_capital_->setPrefix("$ ");
    bt_capital_->setValue(100000);
    params_gl->addWidget(make_param_col("CAPITAL ($)", bt_capital_), 0, 1);

    bt_start_date_ = new QLineEdit;
    bt_start_date_->setPlaceholderText("YYYY-MM-DD");
    bt_start_date_->setText("2024-01-01");
    bt_start_date_->setStyleSheet(kInputStyle());
    bt_start_date_->setFixedHeight(30);
    params_gl->addWidget(make_param_col("START DATE", bt_start_date_), 1, 0);

    bt_end_date_ = new QLineEdit;
    bt_end_date_->setPlaceholderText("YYYY-MM-DD");
    bt_end_date_->setText("2025-01-01");
    bt_end_date_->setStyleSheet(kInputStyle());
    bt_end_date_->setFixedHeight(30);
    params_gl->addWidget(make_param_col("END DATE", bt_end_date_), 1, 1);

    vl->addWidget(params_grid);

    // RUN BACKTEST button
    auto* bt_btn = new QPushButton("RUN BACKTEST", content);
    bt_btn->setCursor(Qt::PointingHandCursor);
    bt_btn->setFixedHeight(36);
    bt_btn->setStyleSheet(
        QString("QPushButton { background: rgba(8,145,178,0.1); color: %1; border: 1px solid %1;"
                " font-size: %2px; font-weight: 700; %3 padding: 6px 24px; }"
                "QPushButton:hover { background: %1; color: %4; }")
            .arg(fincept::ui::colors::CYAN())
            .arg(fincept::ui::fonts::DATA)
            .arg(kMonoFont())
            .arg(fincept::ui::colors::BG_BASE()));
    connect(bt_btn, &QPushButton::clicked, this, &StrategyBuilderPanel::on_backtest);
    vl->addWidget(bt_btn);

    // Status label
    status_label_ = new QLabel("", content);
    status_label_->setWordWrap(true);
    status_label_->setStyleSheet(
        QString("color: %1; font-size: %2px; %3 background: transparent; border: none;")
            .arg(fincept::ui::colors::TEXT_TERTIARY())
            .arg(fincept::ui::fonts::SMALL)
            .arg(kMonoFont()));
    vl->addWidget(status_label_);

    // ── Results area ────────────────────────────────────────────────────────
    auto* results_container = new QWidget(content);
    results_layout_ = new QVBoxLayout(results_container);
    results_layout_->setContentsMargins(0, 4, 0, 0);
    results_layout_->setSpacing(8);

    // Empty state
    bt_empty_label_ = new QLabel("Run a backtest to see results", results_container);
    bt_empty_label_->setAlignment(Qt::AlignCenter);
    bt_empty_label_->setStyleSheet(
        QString("color: %1; font-size: %2px; %3 background: transparent; border: none; padding: 24px;")
            .arg(fincept::ui::colors::TEXT_TERTIARY())
            .arg(fincept::ui::fonts::SMALL)
            .arg(kMonoFont()));
    results_layout_->addWidget(bt_empty_label_);

    // KPI grid — hidden until first result
    kpi_grid_widget_ = new QWidget(results_container);
    kpi_grid_widget_->setVisible(false);

    auto* kpi_gl = new QGridLayout(kpi_grid_widget_);
    kpi_gl->setContentsMargins(0, 0, 0, 0);
    kpi_gl->setSpacing(8);

    // Helper to build one KPI card and wire up its labels
    struct KpiDef {
        QString  label;
        QLabel** val_out;
        QLabel** sub_out;
    };

    QList<KpiDef> kpi_defs = {
        {"TOTAL RETURN",  &kpi_total_return_val_,  &kpi_total_return_sub_},
        {"SHARPE RATIO",  &kpi_sharpe_val_,        &kpi_sharpe_sub_},
        {"MAX DRAWDOWN",  &kpi_max_dd_val_,        &kpi_max_dd_sub_},
        {"WIN RATE",      &kpi_win_rate_val_,      &kpi_win_rate_sub_},
        {"TOTAL TRADES",  &kpi_trades_val_,        &kpi_trades_sub_},
        {"PROFIT FACTOR", &kpi_profit_factor_val_, &kpi_profit_factor_sub_},
    };

    for (int i = 0; i < kpi_defs.size(); ++i) {
        const auto& def = kpi_defs[i];

        auto* card = new QWidget(kpi_grid_widget_);
        card->setObjectName("btKpiCard");
        card->setStyleSheet(
            QString("#btKpiCard { background:%1; border:1px solid %2; border-radius:4px; }")
                .arg(fincept::ui::colors::BG_SURFACE(), fincept::ui::colors::BORDER_DIM()));

        auto* cl = new QVBoxLayout(card);
        cl->setContentsMargins(12, 10, 12, 10);
        cl->setSpacing(2);

        auto* lbl = new QLabel(def.label, card);
        lbl->setStyleSheet(
            QString("color:%1; font-size:%2px; font-family:%3; font-weight:600; letter-spacing:1px;"
                    " background:transparent; border:none;")
                .arg(fincept::ui::colors::TEXT_TERTIARY())
                .arg(fincept::ui::fonts::TINY)
                .arg(fincept::ui::fonts::DATA_FAMILY));
        cl->addWidget(lbl);

        auto* val = new QLabel("—", card);
        val->setStyleSheet(
            QString("color:%1; font-size:%2px; font-family:%3; font-weight:800;"
                    " background:transparent; border:none;")
                .arg(fincept::ui::colors::TEXT_PRIMARY())
                .arg(fincept::ui::fonts::HEADER + 2)
                .arg(fincept::ui::fonts::DATA_FAMILY));
        cl->addWidget(val);
        *def.val_out = val;

        auto* sub = new QLabel("", card);
        sub->setStyleSheet(
            QString("color:%1; font-size:%2px; font-family:%3;"
                    " background:transparent; border:none;")
                .arg(fincept::ui::colors::TEXT_TERTIARY())
                .arg(fincept::ui::fonts::TINY)
                .arg(fincept::ui::fonts::DATA_FAMILY));
        cl->addWidget(sub);
        *def.sub_out = sub;

        kpi_gl->addWidget(card, i / 3, i % 3);
    }

    results_layout_->addWidget(kpi_grid_widget_);
    vl->addWidget(results_container);
    vl->addStretch();

    scroll->setWidget(content);
    root_layout->addWidget(scroll);
    return pane;
}

// ── build_ui: QSplitter shell ────────────────────────────────────────────────

void StrategyBuilderPanel::build_ui() {
    auto* root = new QVBoxLayout(this);
    root->setContentsMargins(0, 0, 0, 0);
    root->setSpacing(0);

    auto* splitter = new QSplitter(Qt::Horizontal, this);
    splitter->setHandleWidth(4);
    splitter->setStyleSheet(
        QString("QSplitter::handle { background: %1; }")
            .arg(fincept::ui::colors::BORDER_DIM()));
    splitter->addWidget(build_left_pane());
    splitter->addWidget(build_right_pane());
    splitter->setStretchFactor(0, 2); // left ~40%
    splitter->setStretchFactor(1, 3); // right ~60%

    root->addWidget(splitter, 1);
    sync_market_type_ui();
}

// ── clear_results ────────────────────────────────────────────────────────────

void StrategyBuilderPanel::sync_market_type_ui() {
    const QString market_type = market_type_combo_ ? market_type_combo_->currentData().toString() : "equity";
    const bool is_polymarket = market_type == "polymarket";

    if (market_id_label_)
        market_id_label_->setText(is_polymarket ? "CONDITION ID" : "MARKET ID");
    if (market_id_edit_) {
        market_id_edit_->setEnabled(is_polymarket);
        if (!is_polymarket)
            market_id_edit_->clear();
        market_id_edit_->setPlaceholderText(is_polymarket ? "Optional condition ID" : "Unused for equity strategies");
    }
    if (symbol_label_)
        symbol_label_->setText(is_polymarket ? "TOKEN ID" : "SYMBOL");
    if (symbol_edit_)
        symbol_edit_->setPlaceholderText(is_polymarket ? "Polymarket token ID" : "RELIANCE.NS");
    if (bt_symbol_label_)
        bt_symbol_label_->setText(is_polymarket ? "TOKEN ID" : "SYMBOL");
    if (bt_symbol_)
        bt_symbol_->setPlaceholderText(is_polymarket ? "Polymarket token ID" : "RELIANCE.NS");
    if (timeframe_combo_) {
        const QString current = timeframe_combo_->currentText();
        const QStringList options = is_polymarket
            ? QStringList{"1h", "4h", "1d", "1w", "1mth"}
            : algo_timeframes();
        QSignalBlocker blocker(timeframe_combo_);
        timeframe_combo_->clear();
        timeframe_combo_->addItems(options);
        const int idx = options.indexOf(current);
        timeframe_combo_->setCurrentIndex(idx >= 0 ? idx : (is_polymarket ? options.indexOf("1d") : 0));
    }
    if (polymarket_config_widget_)
        polymarket_config_widget_->setVisible(is_polymarket);
}

void StrategyBuilderPanel::clear_results() {
    bt_empty_label_->setVisible(true);
    kpi_grid_widget_->setVisible(false);
}

QJsonObject StrategyBuilderPanel::gather_polymarket_bot_config() const {
    QJsonObject cfg;
    cfg["strategy_mode"] = poly_strategy_mode_combo_->currentData().toString();
    cfg["scan_interval_sec"] = static_cast<int>(poly_scan_interval_spin_->value());
    cfg["max_candidates"] = static_cast<int>(poly_max_candidates_spin_->value());
    cfg["sort_by"] = poly_sort_by_combo_->currentData().toString();
    cfg["min_volume"] = poly_min_volume_spin_->value();
    cfg["min_liquidity"] = poly_min_liquidity_spin_->value();
    cfg["max_spread"] = poly_max_spread_spin_->value();
    cfg["min_depth"] = poly_min_depth_spin_->value();
    cfg["min_price"] = poly_min_price_spin_->value();
    cfg["max_price"] = poly_max_price_spin_->value();
    cfg["excluded_categories"] = split_csv_to_json(poly_excluded_categories_edit_->text());
    cfg["excluded_tags"] = split_csv_to_json(poly_excluded_tags_edit_->text());
    cfg["min_time_to_expiry_hours"] = static_cast<int>(poly_min_expiry_spin_->value());
    cfg["freshness_ttl_sec"] = 30;
    cfg["min_edge"] = poly_min_edge_spin_->value();
    cfg["confidence_threshold"] = poly_confidence_spin_->value();
    cfg["momentum_weight"] = poly_momentum_weight_spin_->value();
    cfg["volatility_penalty"] = poly_volatility_penalty_spin_->value();
    cfg["imbalance_weight"] = poly_imbalance_weight_spin_->value();
    cfg["liquidity_weight"] = poly_liquidity_weight_spin_->value();
    cfg["spread_penalty"] = poly_spread_penalty_spin_->value();
    cfg["paper_order_size"] = poly_order_size_spin_->value();
    cfg["max_order_usdc"] = poly_max_order_spin_->value();
    cfg["max_total_exposure"] = poly_max_exposure_spin_->value();
    cfg["daily_loss_limit"] = poly_daily_loss_spin_->value();
    cfg["max_positions"] = static_cast<int>(poly_max_positions_spin_->value());
    cfg["cooldown_minutes"] = static_cast<int>(poly_cooldown_spin_->value());
    cfg["stop_loss_pct"] = poly_stop_loss_spin_->value();
    cfg["take_profit_pct"] = poly_take_profit_spin_->value();
    cfg["trailing_stop_pct"] = poly_trailing_stop_spin_->value();
    return cfg;
}

void StrategyBuilderPanel::load_polymarket_bot_config(const QJsonObject& cfg) {
    auto set_combo = [](QComboBox* combo, const QString& value) {
        const int idx = combo->findData(value);
        combo->setCurrentIndex(idx >= 0 ? idx : 0);
    };

    set_combo(poly_strategy_mode_combo_, cfg.value("strategy_mode").toString("auto_scan"));
    poly_scan_interval_spin_->setValue(json_number(cfg, "scan_interval_sec", 60));
    poly_max_candidates_spin_->setValue(json_number(cfg, "max_candidates", 20));
    set_combo(poly_sort_by_combo_, cfg.value("sort_by").toString("volume"));
    poly_min_volume_spin_->setValue(json_number(cfg, "min_volume", 1000.0));
    poly_min_liquidity_spin_->setValue(json_number(cfg, "min_liquidity", 500.0));
    poly_max_spread_spin_->setValue(json_number(cfg, "max_spread", 0.05));
    poly_min_depth_spin_->setValue(json_number(cfg, "min_depth", 10.0));
    poly_min_price_spin_->setValue(json_number(cfg, "min_price", 0.05));
    poly_max_price_spin_->setValue(json_number(cfg, "max_price", 0.95));
    poly_excluded_categories_edit_->setText(join_json_strings(cfg.value("excluded_categories").toArray()));
    poly_excluded_tags_edit_->setText(join_json_strings(cfg.value("excluded_tags").toArray()));
    poly_min_expiry_spin_->setValue(json_number(cfg, "min_time_to_expiry_hours", 24));
    poly_min_edge_spin_->setValue(json_number(cfg, "min_edge", 0.04));
    poly_confidence_spin_->setValue(json_number(cfg, "confidence_threshold", 0.55));
    poly_momentum_weight_spin_->setValue(json_number(cfg, "momentum_weight", 0.20));
    poly_volatility_penalty_spin_->setValue(json_number(cfg, "volatility_penalty", 0.15));
    poly_imbalance_weight_spin_->setValue(json_number(cfg, "imbalance_weight", 0.20));
    poly_liquidity_weight_spin_->setValue(json_number(cfg, "liquidity_weight", 0.10));
    poly_spread_penalty_spin_->setValue(json_number(cfg, "spread_penalty", 0.20));
    poly_order_size_spin_->setValue(json_number(cfg, "paper_order_size", 10.0));
    poly_max_order_spin_->setValue(json_number(cfg, "max_order_usdc", 25.0));
    poly_max_exposure_spin_->setValue(json_number(cfg, "max_total_exposure", 100.0));
    poly_daily_loss_spin_->setValue(json_number(cfg, "daily_loss_limit", 25.0));
    poly_max_positions_spin_->setValue(json_number(cfg, "max_positions", 5));
    poly_cooldown_spin_->setValue(json_number(cfg, "cooldown_minutes", 10));
    poly_stop_loss_spin_->setValue(json_number(cfg, "stop_loss_pct", 30.0));
    poly_take_profit_spin_->setValue(json_number(cfg, "take_profit_pct", 50.0));
    poly_trailing_stop_spin_->setValue(json_number(cfg, "trailing_stop_pct", 0.0));
}

void StrategyBuilderPanel::load_strategy(const AlgoStrategy& strategy) {
    current_strategy_id_ = strategy.id;
    name_edit_->setText(strategy.name);
    desc_edit_->setText(strategy.description);

    {
        const QSignalBlocker blocker(market_type_combo_);
        const int idx = market_type_combo_->findData(strategy.market_type.isEmpty() ? "equity" : strategy.market_type);
        market_type_combo_->setCurrentIndex(idx >= 0 ? idx : 0);
    }
    market_id_edit_->setText(strategy.market_id);
    symbol_edit_->setText(strategy.symbol);
    sync_market_type_ui();
    timeframe_combo_->setCurrentText(strategy.timeframe);
    entry_logic_combo_->setCurrentText(strategy.entry_logic);
    exit_logic_combo_->setCurrentText(strategy.exit_logic);
    stop_loss_spin_->setValue(strategy.stop_loss);
    take_profit_spin_->setValue(strategy.take_profit);
    trailing_stop_spin_->setValue(strategy.trailing_stop);
    load_polymarket_bot_config(strategy.bot_config);
    bt_symbol_->setText(strategy.symbol);

    auto load_conditions = [this](QVBoxLayout* layout, const QJsonArray& conditions) {
        while (auto* item = layout->takeAt(0)) {
            if (auto* widget = item->widget())
                widget->deleteLater();
            delete item;
        }

        QWidget* parent = layout->parentWidget() ? layout->parentWidget() : this;
        const bool use_empty_row = conditions.isEmpty();
        for (const auto& value : (use_empty_row ? QJsonArray{} : conditions)) {
            auto* row = build_condition_row(parent);
            auto* ind_combo = qobject_cast<QComboBox*>(row->property("ind_combo").value<QObject*>());
            auto* field_combo = qobject_cast<QComboBox*>(row->property("field_combo").value<QObject*>());
            auto* op_combo = qobject_cast<QComboBox*>(row->property("op_combo").value<QObject*>());
            auto* val_spin = qobject_cast<QDoubleSpinBox*>(row->property("val_spin").value<QObject*>());
            const auto cond = value.toObject();
            if (ind_combo) {
                const int idx = ind_combo->findData(cond.value("indicator").toString());
                if (idx >= 0)
                    ind_combo->setCurrentIndex(idx);
            }
            if (field_combo) {
                const int idx = field_combo->findText(cond.value("field").toString());
                if (idx >= 0)
                    field_combo->setCurrentIndex(idx);
            }
            if (op_combo) {
                const int idx = op_combo->findText(cond.value("operator").toString());
                if (idx >= 0)
                    op_combo->setCurrentIndex(idx);
            }
            if (val_spin)
                val_spin->setValue(cond.value("value").toDouble());
            layout->addWidget(row);
        }
        if (use_empty_row)
            layout->addWidget(build_condition_row(parent));
    };

    load_conditions(entry_conditions_layout_, strategy.entry_conditions);
    load_conditions(exit_conditions_layout_, strategy.exit_conditions);
    clear_results();
}

// ── display_backtest_result — Quant Lab KPI card style ───────────────────────

void StrategyBuilderPanel::display_backtest_result(const QJsonObject& payload) {
    bt_empty_label_->setVisible(false);
    kpi_grid_widget_->setVisible(true);

    double total_return  = payload.value("total_return").toDouble();
    double sharpe        = payload.value("sharpe_ratio").toDouble();
    double max_dd        = payload.value("max_drawdown").toDouble();
    int    total_trades  = payload.value("total_trades").toInt();
    double win_rate      = payload.value("win_rate").toDouble();
    double profit_factor = payload.value("profit_factor").toDouble();
    double final_val     = payload.value("final_value").toDouble();

    auto set_kpi = [](QLabel* lbl, const QString& text, const QString& color) {
        lbl->setText(text);
        lbl->setStyleSheet(
            QString("color:%1; font-size:%2px; font-family:%3; font-weight:800;"
                    " background:transparent; border:none;")
                .arg(color)
                .arg(fincept::ui::fonts::HEADER + 2)
                .arg(fincept::ui::fonts::DATA_FAMILY));
    };

    // TOTAL RETURN
    set_kpi(kpi_total_return_val_,
            QString("%1%2%").arg(total_return >= 0 ? "+" : "").arg(total_return, 0, 'f', 2),
            total_return >= 0 ? fincept::ui::colors::POSITIVE : fincept::ui::colors::NEGATIVE);
    kpi_total_return_sub_->setText(
        QString("Final: $%1").arg(final_val, 0, 'f', 0));

    // SHARPE
    set_kpi(kpi_sharpe_val_, QString::number(sharpe, 'f', 3),
            sharpe >= 0.5 ? fincept::ui::colors::POSITIVE : fincept::ui::colors::NEGATIVE);
    kpi_sharpe_sub_->setText(sharpe >= 1.0 ? "Excellent" : sharpe >= 0.5 ? "Good" : "Weak");

    // MAX DRAWDOWN (always red)
    set_kpi(kpi_max_dd_val_,
            QString("-%1%").arg(qAbs(max_dd), 0, 'f', 2),
            fincept::ui::colors::NEGATIVE);
    kpi_max_dd_sub_->setText("Max Drawdown");

    // WIN RATE
    set_kpi(kpi_win_rate_val_,
            QString("%1%").arg(win_rate, 0, 'f', 1),
            win_rate >= 50.0 ? fincept::ui::colors::POSITIVE : fincept::ui::colors::NEGATIVE);
    kpi_win_rate_sub_->setText(win_rate >= 50.0 ? "Above average" : "Below average");

    // TOTAL TRADES
    set_kpi(kpi_trades_val_, QString::number(total_trades), fincept::ui::colors::TEXT_PRIMARY);
    kpi_trades_sub_->setText("Total trades");

    // PROFIT FACTOR
    set_kpi(kpi_profit_factor_val_, QString::number(profit_factor, 'f', 2),
            profit_factor >= 1.0 ? fincept::ui::colors::POSITIVE : fincept::ui::colors::NEGATIVE);
    kpi_profit_factor_sub_->setText(profit_factor >= 1.5 ? "Strong" : profit_factor >= 1.0 ? "Profitable" : "Losing");
}

// ── on_backtest_result ───────────────────────────────────────────────────────

void StrategyBuilderPanel::on_backtest_result(const QJsonObject& payload) {
    status_label_->setText("Backtest complete.");
    status_label_->setStyleSheet(
        QString("color: %1; font-size: %2px; %3 background: transparent; border: none;")
            .arg(fincept::ui::colors::POSITIVE())
            .arg(fincept::ui::fonts::SMALL)
            .arg(kMonoFont()));
    display_backtest_result(payload);
    LOG_INFO("AlgoTrading", "Backtest result displayed");
}

// ── on_save ──────────────────────────────────────────────────────────────────

void StrategyBuilderPanel::on_save() {
    if (name_edit_->text().trimmed().isEmpty()) {
        status_label_->setText("Strategy name is required.");
        status_label_->setStyleSheet(
            QString("color: %1; font-size: %2px; %3 background: transparent; border: none;")
                .arg(fincept::ui::colors::NEGATIVE())
                .arg(fincept::ui::fonts::SMALL)
                .arg(kMonoFont()));
        return;
    }

    AlgoStrategy strategy;
    strategy.id               = current_strategy_id_.isEmpty() ? QUuid::createUuid().toString(QUuid::WithoutBraces)
                                                               : current_strategy_id_;
    strategy.name             = name_edit_->text().trimmed();
    strategy.description      = desc_edit_->text().trimmed();
    strategy.market_type      = market_type_combo_->currentData().toString();
    strategy.market_id        = strategy.market_type == "polymarket" ? market_id_edit_->text().trimmed() : QString();
    strategy.symbol           = symbol_edit_->text().trimmed();
    strategy.timeframe        = timeframe_combo_->currentText();
    strategy.entry_conditions = gather_from_layout(entry_conditions_layout_);
    strategy.exit_conditions  = gather_from_layout(exit_conditions_layout_);
    strategy.entry_logic      = entry_logic_combo_->currentText();
    strategy.exit_logic       = exit_logic_combo_->currentText();
    strategy.stop_loss        = stop_loss_spin_->value();
    strategy.take_profit      = take_profit_spin_->value();
    strategy.trailing_stop    = trailing_stop_spin_->value();
    if (strategy.market_type == "polymarket") {
        strategy.bot_config = gather_polymarket_bot_config();
        strategy.bot_config["strategy_mode"] = "auto_scan";
    }

    status_label_->setText("Saving...");
    status_label_->setStyleSheet(
        QString("color: %1; font-size: %2px; %3 background: transparent; border: none;")
            .arg(fincept::ui::colors::TEXT_SECONDARY())
            .arg(fincept::ui::fonts::SMALL)
            .arg(kMonoFont()));

    AlgoTradingService::instance().save_strategy(strategy);
    LOG_INFO("AlgoTrading", QString("Saving strategy: %1").arg(strategy.name));

    {
        QJsonObject json;
        json["id"]            = strategy.id;
        json["name"]          = strategy.name;
        json["description"]   = strategy.description;
        json["market_type"]   = strategy.market_type;
        json["market_id"]     = strategy.market_id;
        json["symbol"]        = strategy.symbol;
        json["timeframe"]     = strategy.timeframe;
        json["entry_logic"]   = strategy.entry_logic;
        json["exit_logic"]    = strategy.exit_logic;
        json["stop_loss"]     = strategy.stop_loss;
        json["take_profit"]   = strategy.take_profit;
        json["trailing_stop"] = strategy.trailing_stop;
        json["bot_config"]    = strategy.bot_config;

        QJsonArray entry_arr;
        for (const auto& c : strategy.entry_conditions) entry_arr.append(c);
        json["entry_conditions"] = entry_arr;

        QJsonArray exit_arr;
        for (const auto& c : strategy.exit_conditions) exit_arr.append(c);
        json["exit_conditions"] = exit_arr;

        QString safe_name = strategy.name;
        safe_name.replace(QRegularExpression("[^a-zA-Z0-9_\\-]"), "_");
        QString dest = services::FileManagerService::instance().storage_dir() + "/" +
                       safe_name + "_" + strategy.id.left(8) + ".json";

        QFile f(dest);
        if (f.open(QIODevice::WriteOnly | QIODevice::Text)) {
            f.write(QJsonDocument(json).toJson(QJsonDocument::Indented));
            f.close();
            services::FileManagerService::instance().register_file(
                safe_name + "_" + strategy.id.left(8) + ".json",
                strategy.name + ".json", QFileInfo(dest).size(),
                "application/json", "algo_trading");
        }
    }
}

// ── on_backtest ──────────────────────────────────────────────────────────────

void StrategyBuilderPanel::on_backtest() {
    const QString market_type = market_type_combo_->currentData().toString();
    const QString symbol = symbol_edit_->text().trimmed();
    if (symbol.isEmpty()) {
        status_label_->setText(market_type == "polymarket" ? "Enter a token ID for backtesting."
                                                             : "Enter a symbol for backtesting.");
        status_label_->setStyleSheet(
            QString("color: %1; font-size: %2px; %3 background: transparent; border: none;")
                .arg(fincept::ui::colors::NEGATIVE())
                .arg(fincept::ui::fonts::SMALL)
                .arg(kMonoFont()));
        return;
    }

    status_label_->setText("Running backtest...");
    status_label_->setStyleSheet(
        QString("color: %1; font-size: %2px; %3 background: transparent; border: none;")
            .arg(fincept::ui::colors::CYAN())
            .arg(fincept::ui::fonts::SMALL)
            .arg(kMonoFont()));

    QString start_date = bt_start_date_->text().trimmed();
    QString end_date   = bt_end_date_->text().trimmed();
    if (start_date.isEmpty()) start_date = "2024-01-01";
    if (end_date.isEmpty())   end_date   = "2025-01-01";

    QJsonObject params;
    params["strategy_id"] = current_strategy_id_;
    params["name"] = name_edit_->text().trimmed();
    params["market_type"] = market_type;
    params["market_id"] = market_id_edit_->text().trimmed();
    params["symbol"] = symbol;
    params["timeframe"] = timeframe_combo_->currentText();
    params["entry_conditions"] = gather_from_layout(entry_conditions_layout_);
    params["exit_conditions"] = gather_from_layout(exit_conditions_layout_);
    params["entry_logic"] = entry_logic_combo_->currentText();
    params["exit_logic"] = exit_logic_combo_->currentText();
    params["stop_loss"] = stop_loss_spin_->value();
    params["take_profit"] = take_profit_spin_->value();
    params["trailing_stop"] = trailing_stop_spin_->value();
    if (market_type == "polymarket")
        params["bot_config"] = gather_polymarket_bot_config();
    params["start_date"] = start_date;
    params["end_date"] = end_date;
    params["initial_capital"] = bt_capital_->value();

    AlgoTradingService::instance().run_backtest(params);
    LOG_INFO("AlgoTrading", QString("Backtest requested: %1 on %2")
                                 .arg(current_strategy_id_.isEmpty() ? "unsaved" : current_strategy_id_, symbol));
}

// ── on_error ─────────────────────────────────────────────────────────────────

void StrategyBuilderPanel::on_error(const QString& context, const QString& msg) {
    if (status_label_) {
        status_label_->setText(QString("Error [%1]: %2").arg(context, msg));
        status_label_->setStyleSheet(
            QString("color: %1; font-size: %2px; %3 background: transparent; border: none;")
                .arg(fincept::ui::colors::NEGATIVE())
                .arg(fincept::ui::fonts::SMALL)
                .arg(kMonoFont()));
    }
}

} // namespace fincept::screens
