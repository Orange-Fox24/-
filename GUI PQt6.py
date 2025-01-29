import sys
import psycopg2
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QLabel, QMessageBox, QComboBox, QHBoxLayout
)
from PyQt6.QtCore import Qt


class DatabaseManager:
    def __init__(self, db_name, user, password, host='localhost', port='5432'):
        try:
            self.connection = psycopg2.connect(database=db_name, user=user, password=password, host=host, port=port)
            self.cursor = self.connection.cursor()
        except Exception as e:
            QMessageBox.critical(None, "Ошибка подключения к базе данных", str(e))
            sys.exit(1)

    def get_tables(self):
        self.cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
        return [table[0] for table in self.cursor.fetchall()]

    def get_data(self, table_name):
        self.cursor.execute(f"SELECT * FROM {table_name};")
        return self.cursor.fetchall()

    def get_column_names(self, table_name):
        self.cursor.execute(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = %s
            ORDER BY ordinal_position;
        """, (table_name,))
        return [column[0] for column in self.cursor.fetchall()]

    def add_record(self, table_name, values):
        placeholders = ', '.join(['%s'] * len(values))
        self.cursor.execute(f"INSERT INTO {table_name} VALUES (DEFAULT, {placeholders})", values)
        self.connection.commit()

    def delete_record(self, table_name, record_id):
        self.cursor.execute(f"DELETE FROM {table_name} WHERE {table_name[:-1]}_id = %s", (record_id,))
        self.connection.commit()

    def search_data(self, table_name, search_term):
        self.cursor.execute(f"SELECT * FROM {table_name} WHERE name ILIKE %s", (f'%{search_term}%',))
        return self.cursor.fetchall()

    def close(self):
        self.cursor.close()
        self.connection.close()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("БД Скрепочный союз")
        self.showFullScreen()  

        self.db_manager = DatabaseManager('Datsuk', 'postgres', '20062005')

        self.layout = QVBoxLayout()
        self.table_widget = QTableWidget()
        self.layout.addWidget(self.table_widget)

        self.table_selector = QComboBox()
        self.table_selector.addItems(self.db_manager.get_tables())
        self.table_selector.currentTextChanged.connect(self.load_table_data)
        self.layout.addWidget(self.table_selector)

        self.search_input = QLineEdit()
        self.layout.addWidget(QLabel("Поиск:"))
        self.layout.addWidget(self.search_input)

        self.search_button = QPushButton("Найти")
        self.search_button.clicked.connect(self.search_data)
        self.layout.addWidget(self.search_button)

        self.add_button = QPushButton("Добавить запись")
        self.add_button.clicked.connect(self.add_record)
        self.layout.addWidget(self.add_button)

        self.delete_button = QPushButton("Удалить запись")
        self.delete_button.clicked.connect(self.delete_record)
        self.layout.addWidget(self.delete_button)

        self.load_table_data(self.table_selector.currentText())


        self.control_layout = QHBoxLayout()
        self.minimize_button = QPushButton("Свернуть")
        self.minimize_button.clicked.connect(self.showMinimized)
        self.control_layout.addWidget(self.minimize_button)

        self.exit_button = QPushButton("Выйти")
        self.exit_button.clicked.connect(self.close)
        self.control_layout.addWidget(self.exit_button)

        self.layout.addLayout(self.control_layout)

        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

    def load_table_data(self, table_name):
        self.table_widget.setRowCount(0)
        self.table_widget.setColumnCount(0)

        data = self.db_manager.get_data(table_name)
        if data:
            self.table_widget.setColumnCount(len(data[0]))
            self.table_widget.setRowCount(len(data))


            self.table_widget.setHorizontalHeaderLabels(self.db_manager.get_column_names(table_name))

            for row_index, row_data in enumerate(data):
                for column_index, item in enumerate(row_data):
                    self.table_widget.setItem(row_index, column_index, QTableWidgetItem(str(item)))


            for i in range(len(data[0])):
                self.table_widget.resizeColumnToContents(i)

    def search_data(self):
        search_term = self.search_input.text()
        table_name = self.table_selector.currentText()
        results = self.db_manager.search_data(table_name, search_term)


        self.table_widget.setRowCount(0)
        self.table_widget.setColumnCount(0)

        if results:

            column_names = self.db_manager.get_column_names(table_name)
            self.table_widget.setColumnCount(len(column_names))
            self.table_widget.setHorizontalHeaderLabels(column_names)
            self.table_widget.setRowCount(len(results))

            for row_index, row_data in enumerate(results):
                for column_index, item in enumerate(row_data):
                    item_str = str(item)
                    self.table_widget.setItem(row_index, column_index, QTableWidgetItem(item_str))


                    if search_term.lower() in item_str.lower():
                        self.table_widget.item(row_index, column_index).setBackground(Qt.GlobalColor.yellow)


            for i in range(len(column_names)):
                self.table_widget.resizeColumnToContents(i)
        else:
            QMessageBox.information(self, "Результаты поиска", "Записи не найдены.")

    def add_record(self):
        table_name = self.table_selector.currentText()
        column_names = self.db_manager.get_column_names(table_name)

        dialog = QWidget()
        dialog.setWindowTitle("Добавить запись")
        layout = QVBoxLayout()

        inputs = []
        for column in column_names:
            layout.addWidget(QLabel(column))
            input_field = QLineEdit()
            layout.addWidget(input_field)
            inputs.append(input_field)

        button = QPushButton("Сохранить")
        layout.addWidget(button)
        dialog.setLayout(layout)

        def on_submit():
            values = [input_field.text() for input_field in inputs]
            try:
                self.db_manager.add_record(table_name, values)
                self.load_table_data(table_name)
                dialog.close()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))

        button.clicked.connect(on_submit)
        dialog.setLayout(layout)
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        dialog.show()

    def delete_record(self):
        table_name = self.table_selector.currentText()
        record_id = self.get_input("Удалить запись", [f"{table_name[:-1]} ID"])
        if record_id and record_id[0].isdigit():

            reply = QMessageBox.question(self, 'Подтверждение удаления',
                                         f'Вы уверены, что хотите удалить запись с ID {record_id[0]}?',
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

            if reply == QMessageBox.Yes:
                try:
                    self.db_manager.delete_record(table_name, int(record_id[0]))
                    self.load_table_data(table_name)
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", str(e))
        else:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, введите корректный ID.")

    def get_input(self, title, labels):
        dialog = QWidget()
        dialog.setWindowTitle(title)
        layout = QVBoxLayout()
        inputs = []

        for label in labels:
            layout.addWidget(QLabel(label))
            input_field = QLineEdit()
            layout.addWidget(input_field)
            inputs.append(input_field)

        button = QPushButton("Подтвердить")
        layout.addWidget(button)
        dialog.setLayout(layout)

        def on_submit():
            dialog.close()

        button.clicked.connect(on_submit)
        dialog.setLayout(layout)
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        dialog.show()

        dialog.exec()

        return [input_field.text() for input_field in inputs]

    def closeEvent(self, event):
        self.db_manager.close()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())