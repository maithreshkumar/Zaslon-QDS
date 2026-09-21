import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split

data = pd.DataFrame({
    'x':[1,2,3,4],
    'y':[10,20,30,40]
})

x=data[['x']]
y=data['y']

x_train,x_test,y_train,y_test=train_test_split(
    x,y,test_size=0.2,random_state=0
)

m=LinearRegression().fit(x_train,y_train)

print(m.predict([[5]]))