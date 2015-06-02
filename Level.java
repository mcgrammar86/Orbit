import java.util.List;
import java.util.ArrayList;

public class Level {
	
	public static int final WIDTH = 1080;
	public static int final HEIGHT = 1920
	
	private ArrayList<Body> mBodies;
	//private ArrayList<Wormhole> mWormholes;
	protected Spaceship mSpaceship;
	private double mInitialFuel;
	private double mInitialXPosition;
	private double mInitialYPosition;
	private double mGoalX;
	private double mGoalY;
	
	//Constructor
	public Level(ArrayList<Body> bodies, ArrayList<Wormhole> wormholes, double initialFuel,
		double initialX, double initialY, double goalX, double goalY){
		
		mBodies = bodies;
		mWormholes = wormholes;
		mSpaceship = new Spaceship(initialX,initialY,initialFuel);
		
	}
	
	//getters/setters
	
	public void updateLocations(int tick){
		//update spaceship location using gravity, wormholes, and thrust
		
		
		mBodies.updateLocations();
		
		
	}
}
