package edu.cmu.cs.gabriel;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.util.AttributeSet;
import android.view.MotionEvent;
import android.view.View;
import android.util.Log;
import android.media.ThumbnailUtils;

import java.io.File;
import java.io.FileOutputStream;

import edu.cmu.cs.gabriel.network.AnnotationStreamingThread;

public class DrawingView extends View {
    private static final String LOG_TAG = "DrawingView";

    public int width;
    public  int height;
    private Bitmap mBitmap;
    private Canvas mCanvas;
    private Path mPath;
    private Paint mBitmapPaint;
    Context context;
    private Paint circlePaint;
    private Path circlePath;
    private Paint mPaint;

    private AnnotationStreamingThread annotationStreamingThread = null;

    public DrawingView(Context c, AttributeSet attr) {
        super(c, attr);
        context=c;

        mPaint = new Paint();
        mPaint.setAntiAlias(true);
        mPaint.setDither(true);
        mPaint.setColor(Color.GREEN);
        mPaint.setStyle(Paint.Style.STROKE);
        mPaint.setStrokeJoin(Paint.Join.ROUND);
        mPaint.setStrokeCap(Paint.Cap.ROUND);
        mPaint.setStrokeWidth(12);

        mPath = new Path();
        mBitmapPaint = new Paint(Paint.DITHER_FLAG);
        circlePaint = new Paint();
        circlePath = new Path();
        circlePaint.setAntiAlias(true);
        circlePaint.setColor(Color.BLUE);
        circlePaint.setStyle(Paint.Style.STROKE);
        circlePaint.setStrokeJoin(Paint.Join.MITER);
        circlePaint.setStrokeWidth(4f);

        setDrawingCacheEnabled(true);
    }

    public void setup(AnnotationStreamingThread annotationStreamingThread) {
        this.annotationStreamingThread = annotationStreamingThread;
    }

    @Override
    protected void onSizeChanged(int w, int h, int oldw, int oldh) {
        super.onSizeChanged(w, h, oldw, oldh);

        width = w;
        height = h;

        mBitmap = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888);
        mCanvas = new Canvas(mBitmap);
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);

        canvas.drawBitmap( mBitmap, 0, 0, mBitmapPaint);
        canvas.drawPath( mPath,  mPaint);
        canvas.drawPath( circlePath,  circlePaint);
    }

    private float mX, mY;
    private static final float TOUCH_TOLERANCE = 4;

    private void touch_start(float x, float y) {
        mPath.reset();
        mPath.moveTo(x, y);
        mX = x;
        mY = y;
    }

    private void touch_move(float x, float y) {
        float dx = Math.abs(x - mX);
        float dy = Math.abs(y - mY);
        if (dx >= TOUCH_TOLERANCE || dy >= TOUCH_TOLERANCE) {
            mPath.quadTo(mX, mY, (x + mX)/2, (y + mY)/2);
            mX = x;
            mY = y;

            circlePath.reset();
            circlePath.addCircle(mX, mY, 30, Path.Direction.CW);
        }
    }

    private void touch_up() {
        mPath.lineTo(mX, mY);
        circlePath.reset();
        // commit the path to our offscreen
        mCanvas.drawPath(mPath,  mPaint);
        // kill this so we don't double draw
        mPath.reset();
    }

    @Override
    public boolean onTouchEvent(MotionEvent event) {
        float x = event.getX();
        float y = event.getY();

        switch (event.getAction()) {
            case MotionEvent.ACTION_DOWN:
                touch_start(x, y);
                invalidate();
                break;
            case MotionEvent.ACTION_MOVE:
                touch_move(x, y);
                invalidate();
                break;
            case MotionEvent.ACTION_UP:
                touch_up();
                invalidate();
                break;
        }
        return true;
    }

    public void clearDrawing() {
        setDrawingCacheEnabled(false);
        onSizeChanged(width, height, width, height);
        invalidate();
        setDrawingCacheEnabled(true);
    }

    public void saveDrawing(Bitmap whatTheUserSeeBitmap)
    {
        Bitmap whatTheUserDrewBitmap = getDrawingCache();
        // don't forget to clear it (see above) or you just get duplicates

        // NOTE that's an incredibly useful trick for cropping/resizing squares while handling all memory problems etc
        // http://stackoverflow.com/a/17733530/294884
        whatTheUserDrewBitmap = ThumbnailUtils.extractThumbnail(whatTheUserDrewBitmap, 256, 256);

        // you can now save the bitmap to a file, or display it in an ImageView:
        //ImageView testArea = ...
        //testArea.setImageBitmap( whatTheUserDrewBitmap );
        File annotationImage = new File (Const.ROOT_DIR.getAbsolutePath() + File.separator + "sketch.jpg");
        if (annotationImage.exists())
            annotationImage.delete();
        try {
            FileOutputStream out = new FileOutputStream(annotationImage);
            whatTheUserDrewBitmap.compress(Bitmap.CompressFormat.JPEG, 90, out);
            out.flush();
            out.close();
        } catch (Exception e) {
            Log.e(LOG_TAG, "Error saving image: " + e.getMessage());
        }

        if (annotationStreamingThread != null) {
            annotationStreamingThread.push(whatTheUserSeeBitmap, whatTheUserDrewBitmap);
        }
    }
}
