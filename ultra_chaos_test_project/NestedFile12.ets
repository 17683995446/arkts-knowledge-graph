/**
 * 深度嵌套结构测试文件
 */

export class Outer12 {
    middle: Middle12 = new Middle12();
    
    outerMethod(): void {
        this.middle.inner.innerMethod();
    }
}

class Middle12 {
    inner: Inner12 = new Inner12();
    
    middleMethod(): void {
        this.inner.innerMethod();
    }
}

class Inner12 {
    deeplyNested: DeeplyNested12 = new DeeplyNested12();
    
    innerMethod(): void {
        this.deeplyNested.deepMethod();
    }
}

class DeeplyNested12 {
    deepMethod(): void {
        console.log('deeply nested method called');
    }
}
