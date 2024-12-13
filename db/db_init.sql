USE phishing;

DROP TABLE IF EXISTS Historys;
DROP TABLE IF EXISTS Accounts;

CREATE TABLE Accounts
(
    AccountID	INT AUTO_INCREMENT PRIMARY KEY,
    Username	VARCHAR(255) UNIQUE,
    Password	VARCHAR(255)
);

CREATE TABLE Historys (
    HistoryID INT AUTO_INCREMENT PRIMARY KEY,
    AccountID INT,
    analysisType ENUM('URL', 'MSG', 'FILE'),
    analysisContent CHAR(255),
    isMalicious BOOLEAN,
    Confidence INT,
    Report CHAR(255),
    FOREIGN KEY (AccountID) REFERENCES Accounts (AccountID)
);

INSERT INTO Accounts (Username, Password)
VALUES ('123', '123456'),
       ('wopa', 'wopa'),
       ('456', '123456');

INSERT INTO Historys (AccountID, analysisType, analysisContent, isMalicious, Confidence, Report)
VALUES ('1', 'URL', 'www.google.com', false, 100, 'It is obvious safe url');