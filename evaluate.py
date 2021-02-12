from sklearn.metrics import accuracy_score, classification_report, roc_curve, roc_auc_score, log_loss
import numpy as np
import matplotlib.pyplot as plt

def metrics(gbc,X_test,Y_test):

    pred = gbc.predict(X_test)
    probs = gbc.predict_proba(X_test)
    #print "Predicted vs Actual:\n",np.hstack((np.reshape(pred,(len(pred),1)),np.reshape(Y_test,(len(Y_test),1))))
    #print "Probabilities:\n",probs
    print("Log loss: ", log_loss(Y_test, probs))
    print("Accuracy: ", accuracy_score(Y_test,pred))

    print("Classification report: \n", classification_report(Y_test, pred))
    
    print("ROC AUC Score: ", roc_auc_score(Y_test,probs[:,1]))
    fpr,tpr,_ = roc_curve(Y_test,probs[:,1])
    plt.figure(1)
    plt.plot([0, 1], [0, 1])
    plt.plot(fpr, tpr)
    plt.xlabel('False positive rate')
    plt.ylabel('True positive rate')
    plt.title('ROC curve')
    plt.legend(loc='best')
    plt.show()
    
def metrics_multiclass(gbc,X_test,Y_test):

    pred = gbc.predict(X_test)
    probs = gbc.predict_proba(X_test)
    #print "Predicted vs Actual:\n",np.hstack((np.reshape(pred,(len(pred),1)),np.reshape(Y_test,(len(Y_test),1))))
    #print "Probabilities:\n",probs
    print("Log loss: ", log_loss(Y_test, probs))
    print("Accuracy: ", accuracy_score(Y_test,pred))

    print("Classification report: \n", classification_report(Y_test, pred))

def profit():
    pass


def sharpe_ratio():
    pass

def plot_backtest():
    pass
