public class Spaceship {
	private double mX;
	private double mY;
	private double mVx;
	private double mVy;
	private int mFuel;
	private double mThrustAngle;
	private boolean mIsLaunched;
		
	public Spaceship(double initialX, double initialY, double initialFuel){
		mX = initialX;
		mY = initialY;
		mFuel = initialFuel;
		mIsLaunched=false;
	}
	
	public void launch(double xVelocity, double yVelocity){
		mXVelocity = xVelocity;
		mYVelocity = yVelocity;
		mIsLaunched=true;
	}
	
	public boolean isLaunched(){
		return mIsLaunched;
	}
	
	public boolean isInBounds(){
		return (mXPosition >= 0 && mXPosition <= Level.WIDTH
		&& mYPosition >= 0 && mYPosition <= Level.HEIGHT);
	}
	
	public int getIconId(){
		return mIconId;
	}
	
	public void setIconId(int id)[
		mIconId = id;
	}
	
	public double getXPosition(){
		return mXPosition;
	}
	
	public void setXPosition(double xPosition){
		mXPosition = xPosition;
	}
	
	

}
