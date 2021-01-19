package assignment1;

/* config
points = 1
timeout = 10000
*/

public class OtherTests_TimeoutInfiniteLoop implements Runnable {
    @Override
    public void run() {
        boolean result = new MyPrimeChecker().methodWithInfiniteLoop(1234);
        if (result) {
            throw new AssertionError("isPrime() returned incorrect value.");
        }
        System.out.println("Test passed.");
    }
}
