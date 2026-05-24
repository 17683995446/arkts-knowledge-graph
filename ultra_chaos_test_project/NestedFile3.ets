/**
 * 深度嵌套结构测试文件
 */

export class Outer3 {
    middle: Middle3 = new Middle3();
    
    outerMethod(): void {
        this.middle.inner.innerMethod();
    }
}

class Middle3 {
    inner: Inner3 = new Inner3();
    
    middleMethod(): void {
        this.inner.innerMethod();
    }
}

class Inner3 {
    deeplyNested: DeeplyNested3 = new DeeplyNested3();
    
    innerMethod(): void {
        this.deeplyNested.deepMethod();
    }
}

class DeeplyNested3 {
    deepMethod(): void {
        console.log('deeply nested method called');
    }
}
